// Build-time (Node) access to the generated dataset, used by pages'
// `getStaticPaths()` and index/listing pages. Chart data itself is fetched
// client-side from the `public/dataset` copy (see scripts/copy-dataset.mjs)
// so per-case payloads (e.g. contour grids) aren't inlined into every page.
import { readFileSync } from 'node:fs';
import path from 'node:path';

const DATASET_ROOT = path.join(process.cwd(), '..', 'dataset');

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.join(DATASET_ROOT, relativePath), 'utf-8'));
}

/**
 * @typedef {Object} Alignment
 * @property {string} id
 * @property {string} label
 * @property {string} description
 * @property {Array<{name: string} & Record<string, string>>} settings  one row per setting, one column per software
 * @property {Array<{software: string, note: string}>} residual_differences
 * @property {string[]} cases
 */

/**
 * @typedef {Object} Manifest
 * @property {string} generated_at
 * @property {string} wcomp_version
 * @property {Record<string, string>} software_versions
 * @property {Alignment[]} alignments
 */

/** @returns {Manifest} */
export function getManifest() {
  return readJson('manifest.json');
}

/** The alignment shown at the site root; every other alignment lives under `<id>/`. */
export const DEFAULT_ALIGNMENT = 'default';

/** @returns {Alignment[]} */
export function getAlignments() {
  return getManifest().alignments;
}

/** @param {string} alignment @returns {Alignment} */
export function getAlignment(alignment) {
  const found = getAlignments().find((item) => item.id === alignment);
  if (!found) throw new Error(`Unknown alignment '${alignment}'`);
  return found;
}

/**
 * URL of a page in an alignment. `pagePath` is relative to the alignment root,
 * e.g. '' (home) or 'compare/rotor-averaging/'. The default alignment keeps the
 * site-root URLs; others are prefixed with their id.
 * @param {string} base
 * @param {string} alignment
 * @param {string} [pagePath]
 */
export function pageUrl(base, alignment, pagePath = '') {
  return `${base}${alignment === DEFAULT_ALIGNMENT ? '' : `${alignment}/`}${pagePath}`;
}

/** URL (under `base`) of an alignment's copied dataset files, used by client-side fetches. */
export function datasetUrl(base, alignment) {
  return `${base}dataset/${alignment}`;
}

/**
 * @returns {{
 *   coordinates: string,
 *   execution: string,
 *   reference: string,
 *   methods: Array<{
 *     software: string,
 *     method: string,
 *     sample_count: number,
 *     sampling: string,
 *     aggregation: string,
 *     implementation: string,
 *     nodes_y: number[],
 *     nodes_z: number[],
 *     weights: number[]
 *   }>,
 *   cases: Array<{
 *     key: string,
 *     name: string,
 *     formula: string,
 *     description: string,
 *     analytic_area_average: number | null,
 *     field: {axis: number[], values: Array<Array<number | null>>},
 *     results: Array<{
 *       case: string,
 *       software: string,
 *       method: string,
 *       sample_count: number,
 *       aggregation: string,
 *       rotor_average: number,
 *       reference_average: number,
 *       absolute_error: number,
 *       relative_error: number
 *     }>
 *   }>
 * }}
 */
export function getRotorAverageComparison(alignment) {
  return readJson(`${alignment}/rotor_average.json`);
}

/**
 * @returns {{
 *   turbine: {
 *     name: string,
 *     rotor_diameter: number,
 *     hub_height: number,
 *     air_density: number,
 *     cut_in: number,
 *     cut_out: number,
 *     rated_power_kw: number,
 *     curve: {wind_speeds: number[], power_kw: number[], ct: number[]}
 *   },
 *   setup: string,
 *   execution: string,
 *   reference: string,
 *   wind_speeds: number[],
 *   reference_curves: {power_kw: number[], ct: number[]},
 *   results: Array<{
 *     software: string,
 *     turbine_model: string,
 *     inputs: string,
 *     interpolation: string,
 *     out_of_range: string,
 *     implementation: string,
 *     power_kw: number[],
 *     ct: number[],
 *     max_abs_power_error_kw: number,
 *     max_abs_ct_error: number,
 *     max_abs_power_error_in_range_kw: number,
 *     max_abs_ct_error_in_range: number
 *   }>
 * }}
 */
export function getTurbinePerformanceComparison(alignment) {
  return readJson(`${alignment}/turbine_performance.json`);
}

/**
 * @typedef {Object} ModelEntry
 * @property {string} name
 * @property {string} category
 * @property {string[]} software
 * @property {string | null} case
 */

/** @returns {ModelEntry[]} */
export function getModels() {
  return readJson('models.json');
}

/**
 * @typedef {Object} CaseSummary
 * @property {string} scenario
 * @property {string} wake_model
 * @property {string[]} categories
 * @property {number} rotor_diameter
 * @property {number} hub_height
 * @property {number} wind_speed
 * @property {number[]} turbine_locations_d
 * @property {number[]} turbine_yaw_deg
 * @property {string[]} software
 * @property {{
 *   inputs: Array<{category: string, name: string, parameters: Record<string, unknown>}>,
 *   implementations: Array<{
 *     software: string,
 *     models: Array<{category: string, name: string, parameters: Record<string, unknown>}>,
 *     notes: string[]
 *   }>,
 *   notes: string[]
 * }} model_configuration
 * @property {string[]} xsection_labels
 * @property {boolean} has_contour
 * @property {number} xsection_contour_location_d
 */

/** @param {string} alignment @param {string} caseId @returns {CaseSummary} */
export function getCaseSummary(alignment, caseId) {
  return readJson(`${alignment}/cases/${caseId}/case.json`);
}

/** @param {string} alignment @returns {Array<{id: string} & CaseSummary>} */
export function getAllCases(alignment) {
  return getAlignment(alignment).cases.map((id) => ({ id, ...getCaseSummary(alignment, id) }));
}

/**
 * @param {string} alignment
 * @param {string} caseId
 * @returns {Array<{pair: string[], target: string, rmse: number, max_abs: number, mean_abs: number, nrmse: number}>}
 */
export function getCaseMetrics(alignment, caseId) {
  return readJson(`${alignment}/cases/${caseId}/metrics.json`);
}
