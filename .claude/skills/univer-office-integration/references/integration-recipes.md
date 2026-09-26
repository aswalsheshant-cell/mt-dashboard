# Integration recipes from the supplied Univer snapshot

Evidence: `univer-dev/README.md`, `presets/packages/preset-sheets-node-core/README.md`, and `packages/sheets/src/facade/f-{range,workbook,worksheet}.ts`. Root manifest version: 1.0.2; this is a snapshot identifier, not a recommendation to install the newest registry release.

## Browser Sheets preset
The source README uses these imports and initialization. Adapt package versions and lifecycle to the target app. The container must exist and have nonzero height before initialization.

```ts
import { createUniver, LocaleType, mergeLocales } from '@univerjs/presets';
import { UniverSheetsCorePreset } from '@univerjs/preset-sheets-core';
import enUS from '@univerjs/preset-sheets-core/locales/en-US';
import '@univerjs/preset-sheets-core/lib/index.css';

const { univerAPI } = createUniver({
  locale: LocaleType.EN_US,
  locales: { [LocaleType.EN_US]: mergeLocales(enUS) },
  presets: [UniverSheetsCorePreset({ container: 'app' })],
});
univerAPI.createWorkbook({});
```

## Small read/write example
Use only on a newly created example workbook or a user-authorized range. For real tools resolve a supplied workbook and sheet ID instead of relying on active selection.

```ts
const workbook = univerAPI.getActiveWorkbook();
if (!workbook) throw new Error('No workbook is open');
const sheet = workbook.getActiveSheet();
if (!sheet) throw new Error('No worksheet is available');
const range = sheet.getRange('A1:B2');
range.setValues([['Item', 'Quantity'], ['Sample', 2]]);
const observed = range.getValues();
const snapshot = workbook.save();
// Persist snapshot with the application's storage service.
// Verify observed matches the requested values before reporting success.
```

`save()` returns `IWorkbookData`; it does not itself save a file or produce XLSX. `getSheetBySheetId(sheetId)` can return null. Match range shape to input dimensions. Formula calculation may complete later than the write; use the installed formula package's completion mechanism rather than an arbitrary sleep.

## Headless and custom plugin mode
The retained Node preset README identifies `UniverSheetsNodeCorePreset` from `@univerjs/preset-sheets-node-core`. Verify locale and formula requirements against that installed preset. The source distinguishes Node runtime support (>=18.17.0) from monorepo development requirements (>=22.18); the target package manifests remain authoritative.

Plugin mode requires explicit styles, locale merging, plugin registration and Facade side-effect imports. Follow the complete matching example in source-readme.md; omitting registration is a common reason a typed method is unavailable at runtime.

These snippets were checked against the supplied source; they were not executed in a browser or installed Univer runtime as part of packaging.
