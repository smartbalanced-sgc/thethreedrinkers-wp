<?php
/**
 * WP-CLI eval-file script — apply SEO meta to all posts and terms post-import.
 *
 * Reads three CSVs and writes Rank Math meta:
 *   1. descriptions-final.csv   — new/truncated meta descriptions (articles + tags)
 *   2. seo-meta-augmented.csv   — SEO titles, OG data, canonicals (articles + tags)
 *
 * Rank Math meta keys confirmed from source (class-singular.php, class-post-variables.php):
 *   Post:  rank_math_title | rank_math_description | rank_math_canonical_url
 *          rank_math_focus_keyword | rank_math_facebook_title | rank_math_facebook_description
 *          rank_math_twitter_title | rank_math_twitter_description
 *   Term:  same keys via update_term_meta()
 *
 * Run (from WP root after import, with both CSVs in /tmp/):
 *   wp eval-file apply-seo-meta.php --path=/path/to/wordpress
 *
 * Safe to re-run — uses update_post_meta / update_term_meta (idempotent).
 */

$descriptions_csv = '/tmp/descriptions-final.csv';
$meta_csv         = '/tmp/seo-meta-augmented.csv';

if ( ! file_exists( $descriptions_csv ) ) {
	WP_CLI::error( "Missing: $descriptions_csv" );
}
if ( ! file_exists( $meta_csv ) ) {
	WP_CLI::error( "Missing: $meta_csv" );
}

// ─── helpers ────────────────────────────────────────────────────────────────

function csv_rows( $path ) {
	$rows = [];
	$fh   = fopen( $path, 'r' );
	$hdr  = fgetcsv( $fh );
	while ( $row = fgetcsv( $fh ) ) {
		$rows[] = array_combine( $hdr, $row );
	}
	fclose( $fh );
	return $rows;
}

function slug_to_post_id( $slug ) {
	global $wpdb;
	return (int) $wpdb->get_var(
		$wpdb->prepare(
			"SELECT ID FROM {$wpdb->posts}
			 WHERE post_name = %s AND post_type = 'post' AND post_status = 'publish'
			 LIMIT 1",
			$slug
		)
	);
}

function tag_name_to_term( $tag_name ) {
	// Try exact slug match first
	$slug = sanitize_title( $tag_name );
	$term = get_term_by( 'slug', $slug, 'post_tag' );
	if ( $term ) return $term;
	// Fallback: name match
	return get_term_by( 'name', $tag_name, 'post_tag' );
}

// Strip the SS " — The Three Drinkers" suffix from titles (WP site title handles it)
function clean_title( $title ) {
	return trim( preg_replace( '/ [—–-]+ The Three Drinkers\s*$/u', '', $title ) );
}

// ─── Step 1: apply new descriptions ─────────────────────────────────────────

WP_CLI::log( "\n=== Step 1: Apply descriptions ===" );
$desc_rows   = csv_rows( $descriptions_csv );
$desc_ok     = 0;
$desc_skip   = 0;
$desc_notfnd = 0;

foreach ( $desc_rows as $row ) {
	$new_desc = trim( $row['new_description'] );
	if ( ! $new_desc ) { $desc_skip++; continue; }

	if ( $row['type'] === 'article' ) {
		$post_id = slug_to_post_id( $row['slug'] );
		if ( ! $post_id ) { $desc_notfnd++; continue; }
		update_post_meta( $post_id, 'rank_math_description', $new_desc );
		$desc_ok++;

	} elseif ( $row['type'] === 'tag' ) {
		$term = tag_name_to_term( $row['slug'] );
		if ( ! $term ) { $desc_notfnd++; continue; }
		update_term_meta( $term->term_id, 'rank_math_description', $new_desc );
		$desc_ok++;
	}
}

WP_CLI::log( "  Applied: $desc_ok  |  Not found: $desc_notfnd  |  Skipped (empty): $desc_skip" );

// ─── Step 2: apply SEO titles, canonicals, OG from augmented CSV ────────────

WP_CLI::log( "\n=== Step 2: Apply SEO titles, canonicals, OG ===" );
$meta_rows   = csv_rows( $meta_csv );
$meta_ok     = 0;
$meta_skip   = 0;
$meta_notfnd = 0;

$wp_home = untrailingslashit( get_option( 'home' ) );

foreach ( $meta_rows as $row ) {
	$url_type = $row['url_type'] ?? '';
	if ( ! in_array( $url_type, [ 'article', 'tag' ], true ) ) { $meta_skip++; continue; }
	if ( ( $row['http_status'] ?? '' ) !== '200' ) { $meta_skip++; continue; }

	$seo_title   = clean_title( trim( $row['seo_title'] ?? '' ) );
	$og_title    = clean_title( trim( $row['og_title'] ?? '' ) );
	$canonical   = trim( $row['canonical'] ?? '' );

	// Normalise canonical: convert SS domain to WP domain; skip if same as WP default
	$canonical = str_replace(
		'https://www.thethreedrinkers.com',
		$wp_home,
		$canonical
	);

	if ( $url_type === 'article' ) {
		$slug    = trim( $row['slug'] ?? '' );
		$post_id = $slug ? slug_to_post_id( $slug ) : 0;
		if ( ! $post_id ) { $meta_notfnd++; continue; }

		if ( $seo_title ) {
			update_post_meta( $post_id, 'rank_math_title', $seo_title );
		}
		// OG title only if it differs meaningfully from SEO title
		if ( $og_title && $og_title !== $seo_title ) {
			update_post_meta( $post_id, 'rank_math_facebook_title', $og_title );
			update_post_meta( $post_id, 'rank_math_twitter_title', $og_title );
		}
		// Canonical only if it differs from the WP default (/<base>/<slug>/)
		$expected = trailingslashit( $wp_home . '/magazine-content/' . $slug );
		if ( $canonical && $canonical !== $expected ) {
			update_post_meta( $post_id, 'rank_math_canonical_url', $canonical );
		}
		$meta_ok++;

	} elseif ( $url_type === 'tag' ) {
		$raw_tag = trim( $row['url'] ?? '' );
		// Extract tag name from URL
		if ( preg_match( '#/tag/([^/?#]+)#', $raw_tag, $m ) ) {
			$tag_name = urldecode( $m[1] );
		} else {
			$meta_notfnd++; continue;
		}
		$term = tag_name_to_term( $tag_name );
		if ( ! $term ) { $meta_notfnd++; continue; }

		if ( $seo_title ) {
			update_term_meta( $term->term_id, 'rank_math_title', $seo_title );
		}
		$meta_ok++;
	}
}

WP_CLI::log( "  Applied: $meta_ok  |  Not found: $meta_notfnd  |  Skipped: $meta_skip" );
WP_CLI::success( "\nSEO meta apply complete." );
