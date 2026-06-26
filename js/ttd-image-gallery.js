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
						'<span class="ttd-arrow-icon" aria-hidden="true">‹</span><span class="screen-reader-text">Previous</span>',
						'<span class="ttd-arrow-icon" aria-hidden="true">›</span><span class="screen-reader-text">Next</span>'
					]
				} );

				// Parent theme has aggressive CSS overrides on .owl-nav button
				// that beat our external stylesheet's specificity (we saw the
				// computed style stuck at width:120px height:0 bg:transparent
				// despite our !important rules). Force inline styles — inline
				// + !important is the highest CSS priority and beats every
				// external rule unconditionally.
				var $nav = $wrap.find( '.owl-nav' ).first();
				if ( $nav.length ) {
					$nav[ 0 ].style.cssText +=
						';display:flex !important' +
						';visibility:visible !important' +
						';opacity:1 !important' +
						';position:absolute !important' +
						';top:50% !important' +
						';left:0 !important' +
						';right:0 !important' +
						';transform:translateY(-50%) !important' +
						';justify-content:space-between !important' +
						';padding:0 24px !important' +
						';margin:0 !important' +
						';pointer-events:none !important' +
						';z-index:10 !important' +
						';width:auto !important' +
						';height:auto !important' +
						';box-sizing:border-box !important';
				}
				$wrap.find( '.owl-nav button.owl-prev, .owl-nav button.owl-next' ).each( function () {
					this.style.cssText +=
						';display:flex !important' +
						';visibility:visible !important' +
						';opacity:1 !important' +
						';width:44px !important' +
						';height:44px !important' +
						';min-width:44px !important' +
						';min-height:44px !important' +
						';max-width:44px !important' +
						';max-height:44px !important' +
						';background:rgba(0,0,0,0.55) !important' +
						';color:#fff !important' +
						';border:0 !important' +
						';border-radius:50% !important' +
						';align-items:center !important' +
						';justify-content:center !important' +
						';cursor:pointer !important' +
						';pointer-events:auto !important' +
						';padding:0 !important' +
						';margin:0 !important' +
						';font-size:28px !important' +
						';line-height:1 !important' +
						';box-shadow:none !important' +
						// Parent theme uses absolute positioning with negative
						// left/right offsets to push buttons outside the nav
						// container. Force them back into the flex flow so
						// justify-content:space-between on the .owl-nav puts
						// them where we want.
						';position:relative !important' +
						';left:0 !important' +
						';right:auto !important' +
						';top:auto !important' +
						';bottom:auto !important' +
						';transform:none !important' +
						';float:none !important' +
						';flex:0 0 auto !important';
				} );
				$wrap.find( '.owl-nav .ttd-arrow-icon' ).each( function () {
					this.style.cssText +=
						';display:inline-block !important' +
						';font-family:Arial,sans-serif !important' +
						';font-size:28px !important' +
						';font-weight:300 !important' +
						';line-height:1 !important' +
						';color:#fff !important';
				} );
			} );
		} );
	} );
} )( jQuery );
