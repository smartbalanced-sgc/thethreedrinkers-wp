/**
 * Fit the header site-title onto one line.
 *
 * The theme's site title ("The Three Drinkers") sits in a fixed-width centre
 * column between the hamburger and search icons. On narrow screens that column
 * isn't wide enough for the title's font size, so it wraps to two lines. The
 * available width varies by device and by which header variant the theme shows
 * at a given breakpoint, so a static CSS font-size can't reliably guarantee one
 * line. This measures the real layout and shrinks the font only as much as
 * needed to keep the title on a single line.
 *
 * Robustness notes (why earlier static attempts failed):
 *  - Runs again after the web font (Montserrat) loads. The font is wider than
 *    the fallback, so fitting before it loads lets the title re-wrap once it
 *    swaps in. document.fonts.ready handles this.
 *  - Detects wrapping by comparing the element's height with white-space:nowrap
 *    (always one line) vs normal (wraps if too wide). This is container- and
 *    metrics-agnostic — it works no matter which element/column is on screen.
 *  - Targets every visible .site-title, so it fixes whichever header variant
 *    the theme renders at the current width. Titles that already fit (e.g. the
 *    footer) are left untouched.
 *
 * Purely presentational — no markup or SEO impact.
 */
( function () {
	function isVisible( el ) {
		return !! ( el.offsetWidth || el.offsetHeight || el.getClientRects().length );
	}

	function fitOne( el ) {
		// Reset any size we set previously so we re-measure from the CSS size.
		el.style.fontSize = '';
		el.style.display = 'inline-block';

		if ( ! isVisible( el ) ) {
			return;
		}

		var size = parseFloat( window.getComputedStyle( el ).fontSize );
		if ( ! size ) {
			return;
		}

		var guard = 0;
		while ( guard < 400 && size > 10 ) {
			// One-line height (forced) vs natural height (may wrap).
			el.style.whiteSpace = 'nowrap';
			var oneLine = el.offsetHeight;
			el.style.whiteSpace = 'normal';
			var natural = el.offsetHeight;

			// Fits on one line — done.
			if ( natural <= oneLine + 2 ) {
				break;
			}

			size -= 0.5;
			guard += 1;
			el.style.fontSize = size + 'px';
		}
	}

	function fit() {
		var els = document.querySelectorAll( '.site-title' );
		Array.prototype.forEach.call( els, fitOne );
	}

	// Initial run.
	if ( document.readyState === 'loading' ) {
		document.addEventListener( 'DOMContentLoaded', fit );
	} else {
		fit();
	}

	// Re-run once the web font is ready (it's wider than the fallback and can
	// re-trigger a wrap after the first fit).
	if ( document.fonts && document.fonts.ready && typeof document.fonts.ready.then === 'function' ) {
		document.fonts.ready.then( fit );
	}

	// Belt and braces: also after full load.
	window.addEventListener( 'load', fit );

	// Re-fit on resize / orientation change (debounced).
	var timer;
	window.addEventListener( 'resize', function () {
		clearTimeout( timer );
		timer = setTimeout( fit, 150 );
	} );
} )();
