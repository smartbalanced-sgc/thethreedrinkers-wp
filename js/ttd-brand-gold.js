/**
 * Gild the word "Drinkers" in the site title.
 *
 * The Authentic theme prints the site title as a plain text string inside
 * <a class="site-title">…</a> (header, sticky nav, and footer). CSS can't
 * colour a single word inside a text node, so we split the title here and
 * wrap "Drinkers" in <span class="ttd-gold-word">, which style.css paints
 * with a metallic-gold gradient.
 *
 * Front-end only and purely visual: the document <title>, OG tags, RSS and
 * everything WordPress uses for SEO keep the clean plain-text site name —
 * we only touch the rendered header/footer DOM.
 *
 * Defensive: skips any .site-title that contains an <img> (i.e. once a logo
 * image is set, leave it alone), and is idempotent via a data attribute.
 */
( function () {
	function gild() {
		var titles = document.querySelectorAll( '.site-title' );
		Array.prototype.forEach.call( titles, function ( el ) {
			if ( el.getAttribute( 'data-ttd-gilded' ) ) {
				return;
			}
			// If a logo image is present, don't touch the title.
			if ( el.querySelector( 'img' ) ) {
				return;
			}

			var text = el.textContent;
			if ( ! text ) {
				return;
			}

			var word = 'Drinkers';
			var idx  = text.lastIndexOf( word );
			if ( idx === -1 ) {
				return;
			}

			var before = text.slice( 0, idx );
			var after  = text.slice( idx + word.length );

			// Rebuild the link contents: [before] <span.gold>Drinkers</span> [after]
			el.textContent = '';
			if ( before ) {
				el.appendChild( document.createTextNode( before ) );
			}
			var span = document.createElement( 'span' );
			span.className = 'ttd-gold-word';
			span.textContent = word;
			el.appendChild( span );
			if ( after ) {
				el.appendChild( document.createTextNode( after ) );
			}

			el.setAttribute( 'data-ttd-gilded', '1' );
		} );
	}

	if ( document.readyState === 'loading' ) {
		document.addEventListener( 'DOMContentLoaded', gild );
	} else {
		gild();
	}
} )();
