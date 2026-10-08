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
 * @typedef {Object} Manifest
 * @property {string} generated_at
 * @property {string} wcomp_version
 * @property {Record<string, string>} software_versions
 * @property {string[]} cases
 */

/** @returns {Manifest} */
export function getManifest() {
  return readJson('manifest.json');
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
export function getRotorAverageComparison() {
  return readJson('rotor_average.json');
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
export function getTurbinePerformanceComparison() {
  return readJson('turbine_performance.json');
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

/** @param {string} caseId @returns {CaseSummary} */
export function getCaseSummary(caseId) {
  return readJson(`cases/${caseId}/case.json`);
}

/** @returns {Array<{id: string} & CaseSummary>} */
export function getAllCases() {
  return getManifest().cases.map((id) => ({ id, ...getCaseSummary(id) }));
}
