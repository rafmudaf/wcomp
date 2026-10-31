import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

function schemaNameForPath(relativePath) {
  const parts = relativePath.split(path.sep);
  if (relativePath === 'manifest.json') return 'Manifest';
  if (relativePath === 'models.json') return 'ModelRegistry';
  if (relativePath === 'rotor_average.json') return 'RotorAverageDataset';
  if (relativePath === 'turbine_performance.json') return 'TurbinePerformanceDataset';
  if (parts.length === 3 && parts[0] === 'cases' && parts[2] === 'case.json') return 'Case';
  if (parts.length === 3 && parts[0] === 'cases' && parts[2] === 'metrics.json') return 'Metrics';
  if (parts.length >= 5 && parts[0] === 'cases' && parts[2] === 'software') {
    const name = parts.at(-1);
    if (name === 'meta.json') return 'SoftwareMetadata';
    if (['contour.json', 'contour_vertical.json', 'contour_xsection.json'].includes(name)) return 'WakePlane';
    if (name === 'streamwise.json' || parts.at(-2) === 'xsections') return 'WakeProfile';
  }
  throw new Error(`No dataset schema is defined for path: ${relativePath}`);
}

function walkJsonFiles(directory, prefix = '') {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = path.join(prefix, entry.name);
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return walkJsonFiles(fullPath, relativePath);
    return entry.isFile() && entry.name.endsWith('.json') ? [{ fullPath, relativePath }] : [];
  });
}

function validateShape(document, schemaName, source) {
  if (schemaName === 'WakeProfile' && document.x1.length !== document.values.length) {
    throw new Error(`Invalid WakeProfile document at ${source}: x1 and values lengths differ`);
  }
  if (schemaName === 'WakePlane' && new Set([document.x1.length, document.x2.length, document.values.length]).size !== 1) {
    throw new Error(`Invalid WakePlane document at ${source}: x1, x2, and values lengths differ`);
  }
  if (schemaName === 'Case') {
    if (document.turbine_locations_d.length !== document.turbine_yaw_deg.length) {
      throw new Error(`Invalid Case document at ${source}: turbine location and yaw lengths differ`);
    }
    if (document.xsection_labels.length !== Object.keys(document.xsection_locations_d).length ||
      document.xsection_labels.some((label) => !(label in document.xsection_locations_d))) {
      throw new Error(`Invalid Case document at ${source}: cross-section labels and locations differ`);
    }
  }
  if (schemaName === 'RotorAverageDataset') {
    for (const method of document.methods) {
      if ([method.nodes_y.length, method.nodes_z.length, method.weights.length].some((length) => length !== method.sample_count)) {
        throw new Error(`Invalid RotorAverageDataset document at ${source}: method ${method.method} sample arrays differ`);
      }
    }
    for (const item of document.cases) {
      if (item.field.values.length !== item.field.axis.length || item.field.values.some((row) => row.length !== item.field.axis.length)) {
        throw new Error(`Invalid RotorAverageDataset document at ${source}: case ${item.key} field dimensions differ from axis`);
      }
    }
  }
  if (schemaName === 'TurbinePerformanceDataset') {
    const lengths = [
      document.wind_speeds.length,
      document.reference_curves.power_kw.length,
      document.reference_curves.ct.length,
      ...document.results.flatMap((result) => [result.power_kw.length, result.ct.length]),
    ];
    if (new Set(lengths).size !== 1) {
      throw new Error(`Invalid TurbinePerformanceDataset document at ${source}: result series lengths differ from wind_speeds`);
    }
    const curve = document.turbine.curve;
    if (new Set([curve.wind_speeds.length, curve.power_kw.length, curve.ct.length]).size !== 1) {
      throw new Error(`Invalid TurbinePerformanceDataset document at ${source}: turbine curve series lengths differ`);
    }
  }
}

export function validateDataset(datasetRoot) {
  const schema = JSON.parse(readFileSync(path.join(datasetRoot, 'schema.json'), 'utf8'));
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  const validators = new Map(
    Object.keys(schema.$defs).map((name) => [name, ajv.compile({
      $schema: schema.$schema,
      $defs: schema.$defs,
      $ref: `#/$defs/${name}`,
    })])
  );

  for (const { fullPath, relativePath } of walkJsonFiles(datasetRoot)) {
    if (relativePath === 'schema.json') continue;
    const schemaName = schemaNameForPath(relativePath);
    const document = JSON.parse(readFileSync(fullPath, 'utf8'));
    const validate = validators.get(schemaName);
    if (!validate(document)) {
      const details = validate.errors
        .slice(0, 5)
        .map((error) => `${error.instancePath || '/'} ${error.message}`)
        .join('; ');
      throw new Error(`Invalid ${schemaName} document at ${relativePath}: ${details}`);
    }
    validateShape(document, schemaName, relativePath);
  }
}