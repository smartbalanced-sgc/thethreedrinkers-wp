/**
 * Fit the header site-title onto one line.
 *
 * The theme's site title ("The Three Drinkers") sits in a fixed centre column
 * between the hamburger and search icons. On narrow screens that column isn't
 * wide enough for the title's font size, so it wraps to two lines. The exact
 * available width depends on the device and the icon columns, so a static CSS
 * font-size can't reliably guarantee one line — pick too big and it wraps,
 * too small and it's needlessly tiny.
 *
 * This measures the real column width and shrinks the title's font size only
 * as much as needed to fit a single line. On wide screens the natural size
 * already fits, so nothing changes. Runs on load and on resize.
 *
 * Scoped to .header-col-center .site-title so the sticky-nav brand and footer
 * title are untouched. Purely presentational — no markup or SEO impact.
 */
( function () {
	function fitOne( el ) {
		var box = el.parentElement;
		if ( ! box ) {
			return;
		}

		// Force a single line and clear any size we set previously, so we
		// re-measure from the stylesheet's natural size each time.
		el.style.whiteSpace = 'nowrap';
		el.style.display = 'inline-block';
		el.style.fontSize = '';

		var avail = box.clientWidth - 2; // small safety margin
		if ( avail <= 0 ) {
			return;
		}

		var size = parseFloat( window.getComputedStyle( el ).fontSize ) || 28;
		var guard = 0;

		// Shrink in 0.5px steps until the title's single-line width fits.
		while ( el.scrollWidth > avail && size > 10 && guard < 400 ) {
			size -= 0.5;
			guard += 1;
			el.style.fontSize = size + 'px';
		}
	}

	function fit() {
		var els = document.querySelectorAll( '.header-col-center .site-title' );
		Array.prototype.forEach.call( els, fitOne );
	}

	if ( document.readyState === 'loading' ) {
		document.addEventListener( 'DOMContentLoaded', fit );
	} else {
		fit();
	}

	// Re-fit on resize / orientation change (debounced).
	var timer;
	window.addEventListener( 'resize', function () {
		clearTimeout( timer );
		timer = setTimeout( fit, 150 );
	} );
} )();
