/**
 * Convert imported Squarespace image-gallery-wrapper blocks into Owl carousels.
 *
 * The Squarespace WXR exports galleries as:
 *   <div class="image-gallery-wrapper">
 *     <img src="..." />
 *     <img src="..." />
 *   </div>
 *
 * Owl Carousel is already enqueued by the parent theme (Authentic) on every
 * page, so we only add the init code here. Each direct <img> child becomes
 * one slide. Init pattern mirrors inc/scripts.js initCarouselLoop() in the
 * parent theme so behaviour matches existing site carousels.
 */
( function ( $ ) {
	$( function () {
		var $galleries = $( '.entry-content .image-gallery-wrapper, .post-content .image-gallery-wrapper' );

		if ( ! $galleries.length || typeof $.fn.owlCarousel !== 'function' ) {
			return;
		}

		$galleries.each( function () {
			var $wrap = $( this );

			// Skip if already initialised (defensive — pages with the wrapper
			// nested inside another already-init'd carousel would double-fire).
			if ( $wrap.hasClass( 'owl-carousel' ) ) {
				return;
			}

			$wrap.addClass( 'owl-carousel ttd-image-gallery' );

			// Owl expects each slide to be a direct child element; the SS
			// markup is already direct <img> children, but wrapping in <div>
			// gives us a predictable slide container for CSS / responsive rules.
			$wrap.children( 'img' ).each( function () {
				$( this ).wrap( '<div class="ttd-gallery-slide"></div>' );
			} );

			$wrap.imagesLoaded( function () {
				$wrap.owlCarousel( {
					items: 1,
					loop: true,
					nav: true,
					dots: true,
					lazyLoad: true,
					autoHeight: true,
					navText: [
						'<span class="screen-reader-text">Previous</span>',
						'<span class="screen-reader-text">Next</span>'
					]
				} );
			} );
		} );
	} );
} )( jQuery );
