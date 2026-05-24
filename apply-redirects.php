<?php
/**
 * WP-CLI eval-file script — bulk-import redirects into Rank Math's redirect manager.
 *
 * Rank Math has NO CSV import. This script reads redirects.csv and calls
 * RankMath\Redirections\DB::add() directly for each redirect.
 *
 * The sources field requires a serialized array with pattern + comparison keys.
 * Confirmed from class-db.php source.
 *
 * Run:
 *   wp eval-file apply-redirects.php --path=/path/to/wordpress
 *
 * Safe to re-run — checks for existing source patterns before inserting.
 * Pass --dry-run to preview without writing.
 */

$csv_path = '/tmp/redirects.csv';
$dry_run  = in_array( '--dry-run', $GLOBALS['argv'] ?? [], true );

if ( ! file_exists( $csv_path ) ) {
	WP_CLI::error( "Missing: $csv_path" );
}

if ( ! class_exists( 'RankMath\Redirections\DB' ) ) {
	WP_CLI::error( 'Rank Math Redirections class not found. Is Rank Math active and the redirections module enabled?' );
}

$fh  = fopen( $csv_path, 'r' );
$hdr = fgetcsv( $fh );
$ok = $skip = $dupe = $err = 0;

WP_CLI::log( $dry_run ? "\n=== DRY RUN — no changes will be written ===\n" : "\n=== Importing redirects into Rank Math ===\n" );

while ( $row = fgetcsv( $fh ) ) {
	$r = array_combine( $hdr, $row );

	$source  = trim( $r['source_url'] );
	$target  = trim( $r['target_url'] );
	$code    = (int) ( $r['code'] ?? 301 );
	$is_regex = ( (int) ( $r['regex'] ?? 0 ) === 1 );

	if ( ! $source || ! $target ) { $skip++; continue; }

	$comparison = $is_regex ? 'regex' : 'exact';

	$sources = [
		[
			'pattern'    => $source,
			'comparison' => $comparison,
		]
	];

	if ( $dry_run ) {
		WP_CLI::log( "  [$code] $source  →  $target" );
		$ok++;
		continue;
	}

	// Check for existing redirect with same source to avoid duplicates
	global $wpdb;
	$table    = $wpdb->prefix . 'rank_math_redirections';
	$existing = $wpdb->get_var(
		$wpdb->prepare(
			"SELECT id FROM {$table} WHERE sources LIKE %s LIMIT 1",
			'%' . $wpdb->esc_like( $source ) . '%'
		)
	);

	if ( $existing ) {
		$dupe++;
		continue;
	}

	$result = RankMath\Redirections\DB::add( [
		'sources'     => $sources,
		'url_to'      => $target,
		'header_code' => $code,
		'status'      => 'active',
	] );

	if ( $result ) {
		$ok++;
	} else {
		$err++;
		WP_CLI::warning( "Failed to insert: $source" );
	}
}

fclose( $fh );

WP_CLI::log( "\nDone." );
WP_CLI::log( "  Inserted: $ok" );
WP_CLI::log( "  Duplicates skipped: $dupe" );
WP_CLI::log( "  Empty rows skipped: $skip" );
if ( $err ) WP_CLI::warning( "  Errors: $err" );
if ( ! $dry_run ) WP_CLI::success( "Redirects imported into Rank Math." );
