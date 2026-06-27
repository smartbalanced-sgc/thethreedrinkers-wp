<?php
/**
 * Include Theme Functions
 *
 * @package Authentic Child Theme
 * @subpackage Functions
 * @version 1.0.0
 */

/**
 * Setup Child Theme
 */
function csco_setup_child_theme() {
	// Add Child Theme Text Domain.
	load_child_theme_textdomain( 'authentic', get_stylesheet_directory() . '/languages' );
}

add_action( 'after_setup_theme', 'csco_setup_child_theme', 99 );

/**
 * Enqueue Child Theme Assets
 */
function csco_child_assets() {
	if ( ! is_admin() ) {
		// Version-stamp with the file's modification time so every edit to
		// style.css produces a unique URL and busts browser / server caches.
		// A fixed version (e.g. the theme's 1.0.0) makes browsers serve a
		// stale cached stylesheet indefinitely after a deploy.
		$css_path = get_stylesheet_directory() . '/style.css';
		$version  = file_exists( $css_path ) ? filemtime( $css_path ) : wp_get_theme()->get( 'Version' );
		wp_enqueue_style( 'csco_child_css', trailingslashit( get_stylesheet_directory_uri() ) . 'style.css', array(), $version, 'all' );
	}
}

add_action( 'wp_enqueue_scripts', 'csco_child_assets', 99 );

/**
 * Add your custom code below this comment.
 */

/**
 * Initialise Owl Carousel on imported Squarespace .image-gallery-wrapper blocks.
 *
 * Only loads on singular posts that actually contain the wrapper, so 1,400+
 * non-gallery posts pay zero cost. The parent theme enqueues owl-carousel and
 * imagesloaded globally, so we declare them as deps to guarantee load order.
 */
function ttd_enqueue_image_gallery_carousel() {
	if ( ! is_singular( 'post' ) ) {
		return;
	}

	$post = get_post();
	if ( ! $post || strpos( $post->post_content, 'image-gallery-wrapper' ) === false ) {
		return;
	}

	$rel  = 'js/ttd-image-gallery.js';
	$path = trailingslashit( get_stylesheet_directory() ) . $rel;
	$url  = trailingslashit( get_stylesheet_directory_uri() ) . $rel;
	$ver  = file_exists( $path ) ? filemtime( $path ) : wp_get_theme()->get( 'Version' );

	wp_enqueue_script(
		'ttd-image-gallery',
		$url,
		array( 'jquery', 'owl-carousel', 'imagesloaded' ),
		$ver,
		true
	);
}
add_action( 'wp_enqueue_scripts', 'ttd_enqueue_image_gallery_carousel', 100 );

/**
 * Enqueue the title-fit script site-wide.
 *
 * Shrinks the header site title just enough to fit one line in its column
 * (see js/ttd-fit-title.js). The header appears on every front-end page.
 * No jQuery dependency.
 */
function ttd_enqueue_fit_title() {
	if ( is_admin() ) {
		return;
	}
	$rel  = 'js/ttd-fit-title.js';
	$path = trailingslashit( get_stylesheet_directory() ) . $rel;
	$url  = trailingslashit( get_stylesheet_directory_uri() ) . $rel;
	$ver  = file_exists( $path ) ? filemtime( $path ) : wp_get_theme()->get( 'Version' );

	wp_enqueue_script( 'ttd-fit-title', $url, array(), $ver, true );
}
add_action( 'wp_enqueue_scripts', 'ttd_enqueue_fit_title', 100 );

/**
 * Suppress the theme's featured-image hero on single posts whose body already
 * starts with that same image.
 *
 * Background: imported Squarespace posts often begin with an image (a single
 * lead image or a gallery/carousel). We still assign those posts a featured
 * image so widgets, archives, the homepage and social/OG share cards have a
 * thumbnail — but the theme renders the featured image as a large hero at the
 * top of the single post, directly above the body's identical lead image,
 * which reads as a duplicate.
 *
 * apply-hero-suppression.php scans posts and sets the _ttd_suppress_hero meta
 * on every post whose content starts with an image. Here we turn that flag
 * into a body class so style.css can hide section.post-media on just those
 * posts. Posts that start with text keep their hero (no duplication there).
 */
function ttd_suppress_hero_body_class( $classes ) {
	if ( is_singular( 'post' ) ) {
		$post = get_post();
		if ( $post && get_post_meta( $post->ID, '_ttd_suppress_hero', true ) ) {
			$classes[] = 'ttd-hero-suppressed';
		}
	}
	return $classes;
}
add_filter( 'body_class', 'ttd_suppress_hero_body_class' );

