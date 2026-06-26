<?php
/**
 * WP-CLI eval-file script — flag single posts whose body starts with an image
 * so the theme's featured-image hero can be hidden on just those posts.
 *
 * The problem this solves
 * -----------------------
 * The Authentic theme renders a post's featured image as a large hero banner
 * at the very top of the single-post view. Many imported Squarespace posts
 * begin their body with that same image — either a single lead image or a
 * gallery/carousel. We still want a featured image on these posts (widgets,
 * category archives, the homepage, and social/OG share cards all need a
 * thumbnail), but showing the hero directly above an identical body image
 * reads as a duplicate.
 *
 * What it does
 * ------------
 * Scans published posts and, for each one whose CONTENT STARTS WITH AN IMAGE,
 * sets the _ttd_suppress_hero post meta to '1'. Posts that start with text
 * have the flag removed (idempotent — safe to re-run after edits/imports).
 *
 * functions.php turns that flag into a body class (ttd-hero-suppressed), and
 * style.css hides section.post-media for that class. Posts that start with
 * text keep their hero — there's no duplication there.
 *
 * Run AFTER apply-images.php and apply-featured-images.php (so content images
 * are localized and featured images are assigned), though order doesn't affect
 * correctness — this script only reads where the body begins.
 *
 * Run:
 *   wp eval-file apply-hero-suppression.php --path=/path/to/wordpress
 *
 * Flags:
 *   --dry-run    Preview what would change, no writes.
 *   --post-id=N  Process only this specific post (useful for testing).
 */

if ( ! defined( 'ABSPATH' ) || ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	exit( "Run via: wp eval-file apply-hero-suppression.php\n" );
}

$argv    = $GLOBALS['argv'] ?? [];
$dry_run = in_array( '--dry-run', $argv, true );
$only_id = 0;
foreach ( $argv as $a ) {
	if ( strpos( $a, '--post-id=' ) === 0 ) {
		$only_id = (int) substr( $a, 10 );
	}
}

/**
 * Does the post body begin with an image?
 *
 * Strips any leading whitespace, HTML/block comments, empty paragraphs and
 * line breaks, then checks whether the first real element is image-bearing:
 *   - a Squarespace gallery/carousel wrapper (.image-gallery-wrapper)
 *   - a bare <img>, or an <img> wrapped only in opening tags (no text before
 *     it) such as <figure>, <a>, <p>, <div>, <span>
 *
 * Returns false when the content leads with text, a heading, a list, etc.
 */
function ttd_content_starts_with_image( $content ) {
	if ( ! is_string( $content ) || '' === trim( $content ) ) {
		return false;
	}

	$c = $content;

	// Peel off anything visually-empty at the front, repeatedly, until stable.
	$prev = null;
	while ( $c !== $prev ) {
		$prev = $c;
		$c    = ltrim( $c );
		// Leading HTML or Gutenberg block comments: <!-- ... -->
		$c = preg_replace( '/^<!--.*?-->\s*/s', '', $c, 1 );
		// Leading empty paragraph: <p> with only whitespace / &nbsp; / <br>
		$c = preg_replace( '/^<p[^>]*>(?:\s|&nbsp;|<br\s*\/?>)*<\/p>\s*/i', '', $c, 1 );
		// Leading stray break or non-breaking space
		$c = preg_replace( '/^(?:&nbsp;|<br\s*\/?>)\s*/i', '', $c, 1 );
	}

	// Squarespace gallery / carousel wrapper.
	if ( preg_match( '/^<div[^>]*class=["\'][^"\']*image-gallery-wrapper/i', $c ) ) {
		return true;
	}

	// Bare <img>, or <img> nested only inside opening wrapper tags with no
	// text in between (whitespace allowed). Matches:
	//   <img ...>            <p><img ...>           <figure><img ...>
	//   <a href><img ...>    <div><div><img ...>    <figure><a><img ...>
	if ( preg_match( '/^(?:<(?:figure|a|p|div|span)[^>]*>\s*)*<img[\s>]/i', $c ) ) {
		return true;
	}

	return false;
}

WP_CLI::log( $dry_run
	? "\n=== DRY RUN — no writes ===\n"
	: "\n=== Flagging posts whose body starts with an image (hero suppression) ===\n"
);

global $wpdb;

if ( $only_id ) {
	$ids = [ $only_id ];
} else {
	$ids = $wpdb->get_col(
		"SELECT ID FROM {$wpdb->posts}
		 WHERE post_type = 'post'
		   AND post_status = 'publish'
		 ORDER BY ID ASC"
	);
}

$total = count( $ids );
WP_CLI::log( "Posts to evaluate: $total\n" );

if ( ! $total ) {
	WP_CLI::success( 'Nothing to do.' );
	return;
}

$flagged   = 0;  // newly set
$cleared   = 0;  // flag removed (no longer image-first)
$unchanged = 0;

foreach ( $ids as $post_id ) {
	$post = get_post( $post_id );
	if ( ! $post ) {
		continue;
	}

	$should_suppress = ttd_content_starts_with_image( $post->post_content );
	$currently       = (bool) get_post_meta( $post_id, '_ttd_suppress_hero', true );

	if ( $should_suppress === $currently ) {
		$unchanged++;
		continue;
	}

	if ( $should_suppress ) {
		if ( ! $dry_run ) {
			update_post_meta( $post_id, '_ttd_suppress_hero', '1' );
		}
		WP_CLI::log( "  ✓ suppress hero on {$post_id} \"{$post->post_title}\"" );
		$flagged++;
	} else {
		if ( ! $dry_run ) {
			delete_post_meta( $post_id, '_ttd_suppress_hero' );
		}
		WP_CLI::log( "  – clear flag on {$post_id} \"{$post->post_title}\" (starts with text)" );
		$cleared++;
	}
}

WP_CLI::log( "\nDone." );
WP_CLI::log( "  Posts evaluated:        $total" );
WP_CLI::log( "  Newly flagged (hide):   $flagged" );
WP_CLI::log( "  Flag cleared:           $cleared" );
WP_CLI::log( "  Unchanged:              $unchanged" );

if ( ! $dry_run ) {
	WP_CLI::success( 'Hero suppression flags applied.' );
}
