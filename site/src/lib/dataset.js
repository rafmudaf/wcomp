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
