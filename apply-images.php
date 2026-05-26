<?php
/**
 * WP-CLI eval-file script — sideload external (Squarespace CDN) images
 * referenced in post content into the WP Media Library, then rewrite the
 * post content to use the local URLs.
 *
 * Replaces the Ali Irani "Auto Upload Images" plugin (unmaintained for 3 years)
 * with a transparent, in-repo equivalent that:
 *   - Scans posts AND pages for <img src="..."> referencing the configured
 *     external hosts (Squarespace CDN by default).
 *   - Downloads each unique URL once (per-run dedup + per-URL idempotency).
 *   - Sideloads via WP's native wp_handle_sideload() — same API the import
 *     plugins use, but called directly so we control filename preservation,
 *     alt-text copying, and error handling.
 *   - Updates post_content with the new local URLs.
 *   - Logs everything; safe to re-run (skips URLs already in Media Library).
 *
 * Run:
 *   wp eval-file apply-images.php --path=/path/to/wordpress
 *
 * Flags:
 *   --dry-run   Show what would happen without downloading or modifying posts.
 *   --limit=N   Process only N posts (useful for incremental runs).
 *   --post-id=N Process only this specific post (useful for testing).
 */

if ( ! defined( 'ABSPATH' ) || ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	exit( "Run via: wp eval-file apply-images.php\n" );
}

// WP doesn't load the upload helpers by default in CLI context.
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
require_once ABSPATH . 'wp-admin/includes/media.php';

// ─── Configuration ─────────────────────────────────────────────────────────

// External image hosts to capture. Any <img src> matching these patterns will
// be downloaded and replaced. Add more if you find others in your content.
$EXTERNAL_HOSTS = [
	'images.squarespace-cdn.com',
	'static1.squarespace.com',
	'images.squarespace.com',
	'static.squarespace.com',
];

$POST_TYPES = [ 'post', 'page' ];
$BATCH_SIZE = 100;                                  // posts per query page
$REQUEST_TIMEOUT = 60;                              // seconds per download

// ─── Args ──────────────────────────────────────────────────────────────────

$argv     = $GLOBALS['argv'] ?? [];
$dry_run  = in_array( '--dry-run', $argv, true );
$limit    = 0;
$only_id  = 0;
foreach ( $argv as $a ) {
	if ( strpos( $a, '--limit=' ) === 0 ) {
		$limit = (int) substr( $a, 8 );
	}
	if ( strpos( $a, '--post-id=' ) === 0 ) {
		$only_id = (int) substr( $a, 10 );
	}
}

WP_CLI::log( $dry_run
	? "\n=== DRY RUN — no downloads or writes ===\n"
	: "\n=== Sideloading external images into Media Library ===\n"
);
WP_CLI::log( "External hosts watched: " . implode( ', ', $EXTERNAL_HOSTS ) );
if ( $limit )   WP_CLI::log( "Limit:    $limit posts" );
if ( $only_id ) WP_CLI::log( "Post ID:  $only_id (only this one)" );

// ─── Per-run URL → attachment URL cache (avoids re-downloading the same image
// when it's referenced by multiple posts within one run). ───────────────────

$url_cache = [];

// ─── Helpers ────────────────────────────────────────────────────────────────

/**
 * Check whether we've already sideloaded this URL in a previous run by
 * looking up an attachment with matching _ttd_source_url meta.
 */
function ttd_find_existing_attachment( $url ) {
	global $wpdb;
	$attachment_id = (int) $wpdb->get_var( $wpdb->prepare(
		"SELECT post_id FROM {$wpdb->postmeta}
		 WHERE meta_key = '_ttd_source_url' AND meta_value = %s LIMIT 1",
		$url
	) );
	if ( ! $attachment_id ) {
		return null;
	}
	$local = wp_get_attachment_url( $attachment_id );
	return $local ? $local : null;
}

/**
 * Download an external URL and add it to the Media Library.
 * Returns the new local attachment URL, or false on failure.
 * Records the original URL in _ttd_source_url postmeta so subsequent runs
 * can find it without re-downloading.
 */
function ttd_sideload_url( $url, $request_timeout ) {
	// Strip query string when deriving filename (SS uses ?format=original)
	$path     = wp_parse_url( $url, PHP_URL_PATH );
	$basename = $path ? basename( $path ) : '';

	// Only accept the basename if it ends with a recognised image extension.
	// SS URLs sometimes contain a dot mid-name (e.g. "...thethreedrinkers.com...")
	// which our previous heuristic mistook for a file extension, causing WP to
	// reject the upload as an unknown MIME type.
	$valid_image_ext = '/\.(jpe?g|png|gif|webp|avif|svg)$/i';
	if ( ! $basename || ! preg_match( $valid_image_ext, $basename ) ) {
		// Derive a safe filename. SS exports are overwhelmingly JPG; the actual
		// MIME type is verified by wp_handle_sideload() after download, so a
		// .jpg suffix here is a safe default even if the file is something else
		// (sideload will reject mismatches outright).
		$basename = 'ttd-import-' . substr( md5( $url ), 0, 12 ) . '.jpg';
	}
	// Sanitize after extension detection so we don't strip the . from the ext
	$basename = sanitize_file_name( $basename );

	$tmp = download_url( $url, $request_timeout );
	if ( is_wp_error( $tmp ) ) {
		WP_CLI::warning( "  download_url failed: $url — " . $tmp->get_error_message() );
		return false;
	}

	$file_array = [
		'name'     => $basename,
		'tmp_name' => $tmp,
	];

	$attachment_id = media_handle_sideload( $file_array, 0 );

	if ( is_wp_error( $attachment_id ) ) {
		@unlink( $tmp );
		WP_CLI::warning( "  sideload failed: $url — " . $attachment_id->get_error_message() );
		return false;
	}

	// Remember the source URL so we can detect duplicates on re-runs
	update_post_meta( $attachment_id, '_ttd_source_url', $url );

	$local_url = wp_get_attachment_url( $attachment_id );
	return $local_url ? $local_url : false;
}

/**
 * Build a regex matching <img src="..."> where the host matches one of ours.
 */
function ttd_build_img_regex( array $hosts ) {
	$alternation = implode( '|', array_map(
		function ( $h ) { return preg_quote( $h, '#' ); },
		$hosts
	) );
	// Match img src OR srcset entries OR <a href="..."> linking to SS images
	// (galleries sometimes wrap <img> in an <a> pointing at the same CDN).
	// Capture group 1 = the URL; group 0 = the whole match.
	return '#https?://(?:' . $alternation . ')/[^\s"\'<>]+#i';
}

// ─── Main loop ──────────────────────────────────────────────────────────────

global $wpdb;
$post_types_in = "'" . implode( "','", array_map( 'esc_sql', $POST_TYPES ) ) . "'";

if ( $only_id ) {
	$ids = [ $only_id ];
} else {
	// Get only posts that actually contain one of the external hosts
	$host_likes = [];
	foreach ( $EXTERNAL_HOSTS as $h ) {
		$host_likes[] = $wpdb->prepare( 'post_content LIKE %s', '%' . $wpdb->esc_like( $h ) . '%' );
	}
	$where = '(' . implode( ' OR ', $host_likes ) . ')';
	$sql   = "SELECT ID FROM {$wpdb->posts}
	          WHERE post_type IN ($post_types_in)
	            AND post_status IN ('publish', 'draft', 'pending', 'private')
	            AND $where
	          ORDER BY ID ASC";
	if ( $limit ) {
		$sql .= " LIMIT " . (int) $limit;
	}
	$ids = $wpdb->get_col( $sql );
}

$total_posts = count( $ids );
WP_CLI::log( "\nPosts with external images: $total_posts\n" );

if ( ! $total_posts ) {
	WP_CLI::success( 'Nothing to do.' );
	return;
}

$regex          = ttd_build_img_regex( $EXTERNAL_HOSTS );
$posts_updated  = 0;
$urls_downloaded = 0;
$urls_cached    = 0;
$urls_failed    = 0;
$progress       = \WP_CLI\Utils\make_progress_bar( 'Processing posts', $total_posts );

foreach ( $ids as $post_id ) {
	$post = get_post( $post_id );
	if ( ! $post ) {
		$progress->tick();
		continue;
	}

	$content       = $post->post_content;
	$updated       = $content;
	$matches       = [];
	preg_match_all( $regex, $content, $matches );
	$unique_urls   = array_unique( $matches[0] ?? [] );
	$post_changed  = false;

	foreach ( $unique_urls as $external_url ) {
		// Resolve to a local URL via cache → DB lookup → fresh download
		if ( isset( $url_cache[ $external_url ] ) ) {
			$local_url = $url_cache[ $external_url ];
			$urls_cached++;
		} else {
			$existing = ttd_find_existing_attachment( $external_url );
			if ( $existing ) {
				$local_url = $existing;
				$url_cache[ $external_url ] = $local_url;
				$urls_cached++;
			} elseif ( $dry_run ) {
				$local_url = '[DRY-RUN-PLACEHOLDER]';
				$urls_downloaded++;
			} else {
				$local_url = ttd_sideload_url( $external_url, $REQUEST_TIMEOUT );
				if ( ! $local_url ) {
					$urls_failed++;
					continue;
				}
				$url_cache[ $external_url ] = $local_url;
				$urls_downloaded++;
			}
		}

		if ( ! $dry_run && $local_url !== '[DRY-RUN-PLACEHOLDER]' ) {
			$updated = str_replace( $external_url, $local_url, $updated );
			$post_changed = true;
		}
	}

	if ( $post_changed && $updated !== $content ) {
		wp_update_post( [
			'ID'           => $post_id,
			'post_content' => $updated,
		] );
		$posts_updated++;
	}

	$progress->tick();
}

$progress->finish();

WP_CLI::log( "\nDone." );
WP_CLI::log( "  Posts scanned:        $total_posts" );
WP_CLI::log( "  Posts updated:        $posts_updated" );
WP_CLI::log( "  Images downloaded:    $urls_downloaded" );
WP_CLI::log( "  Images cached/reused: $urls_cached" );
if ( $urls_failed ) {
	WP_CLI::warning( "  Image failures: $urls_failed (see warnings above)" );
}
if ( ! $dry_run ) {
	WP_CLI::success( 'Image sideload complete.' );
}
