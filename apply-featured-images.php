<?php
/**
 * WP-CLI eval-file script — auto-assign featured images for posts missing them.
 *
 * After the SS import, some posts have no _thumbnail_id (no featured image)
 * because the original SS post never had one — typically travel/gallery posts
 * where the writer expected the carousel itself to be the visual hook. WP
 * theme widgets (Featured Posts, Trending Posts, Recent Posts) need a
 * featured image to render properly — without one, the post shows as a
 * blank tile.
 *
 * This script:
 *   1. Finds every published post that has no _thumbnail_id.
 *   2. Looks at post_content for the first <img src=...> referencing a local
 *      WP upload URL (i.e. an image already in the Media Library).
 *   3. Finds the attachment ID for that URL.
 *   4. Sets it as the post's featured image via update_post_meta().
 *
 * Run AFTER apply-images.php has localized all inline images, otherwise the
 * first <img> URL might still point at an external host with no matching
 * attachment.
 *
 * Run:
 *   wp eval-file apply-featured-images.php --path=/path/to/wordpress
 *
 * Flags:
 *   --dry-run    Preview what would be assigned, no writes.
 *   --post-id=N  Process only this specific post (useful for testing).
 *
 * Safe to re-run. Posts that already have a featured image are skipped.
 */

if ( ! defined( 'ABSPATH' ) || ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	exit( "Run via: wp eval-file apply-featured-images.php\n" );
}

$argv    = $GLOBALS['argv'] ?? [];
$dry_run = in_array( '--dry-run', $argv, true );
$only_id = 0;
foreach ( $argv as $a ) {
	if ( strpos( $a, '--post-id=' ) === 0 ) {
		$only_id = (int) substr( $a, 10 );
	}
}

WP_CLI::log( $dry_run
	? "\n=== DRY RUN — no writes ===\n"
	: "\n=== Auto-assigning featured images for posts without one ===\n"
);

global $wpdb;
$site_url = home_url();
$uploads  = wp_upload_dir();
$local_base_url = $uploads['baseurl']; // e.g. https://ttd.bringit.ph/wp-content/uploads

// Posts with no _thumbnail_id meta key at all
if ( $only_id ) {
	$ids = [ $only_id ];
} else {
	$ids = $wpdb->get_col(
		"SELECT p.ID FROM {$wpdb->posts} p
		 LEFT JOIN {$wpdb->postmeta} pm
		   ON pm.post_id = p.ID AND pm.meta_key = '_thumbnail_id'
		 WHERE p.post_type IN ('post','page')
		   AND p.post_status = 'publish'
		   AND pm.meta_id IS NULL
		 ORDER BY p.ID ASC"
	);
}

$total = count( $ids );
WP_CLI::log( "Posts without featured image: $total\n" );

if ( ! $total ) {
	WP_CLI::success( 'Nothing to do — all posts already have featured images.' );
	return;
}

$assigned = 0;
$no_image_found = 0;
$attachment_lookup_failed = 0;

foreach ( $ids as $post_id ) {
	$post = get_post( $post_id );
	if ( ! $post ) continue;

	// Find the first <img> in post_content that points at our own upload dir
	$img_url = '';
	if ( preg_match_all( '#<img[^>]+src=["\']([^"\']+)["\']#i', $post->post_content, $matches ) ) {
		foreach ( $matches[1] as $candidate ) {
			if ( strpos( $candidate, $local_base_url ) === 0 ) {
				$img_url = $candidate;
				break;
			}
		}
	}

	if ( ! $img_url ) {
		WP_CLI::log( "  skip post {$post_id} \"{$post->post_title}\" — no local image in content" );
		$no_image_found++;
		continue;
	}

	// Map URL → attachment ID
	$attachment_id = attachment_url_to_postid( $img_url );

	// Fallback: strip query string / size suffix and retry
	if ( ! $attachment_id ) {
		$stripped = preg_replace( '/-\d+x\d+(\.\w+)$/', '$1', $img_url );
		if ( $stripped !== $img_url ) {
			$attachment_id = attachment_url_to_postid( $stripped );
		}
	}

	if ( ! $attachment_id ) {
		WP_CLI::log( "  ⚠ post {$post_id} \"{$post->post_title}\" — couldn't find attachment for: {$img_url}" );
		$attachment_lookup_failed++;
		continue;
	}

	if ( $dry_run ) {
		WP_CLI::log( "  would set featured image for post {$post_id} \"{$post->post_title}\" → attachment {$attachment_id}" );
	} else {
		update_post_meta( $post_id, '_thumbnail_id', $attachment_id );
		WP_CLI::log( "  ✓ post {$post_id} \"{$post->post_title}\" → attachment {$attachment_id}" );
	}
	$assigned++;
}

WP_CLI::log( "\nDone." );
WP_CLI::log( "  Featured images assigned:   $assigned" );
WP_CLI::log( "  Skipped (no local image):   $no_image_found" );
WP_CLI::log( "  Skipped (attachment lookup failed): $attachment_lookup_failed" );

if ( ! $dry_run ) {
	WP_CLI::success( 'Featured images applied.' );
}
