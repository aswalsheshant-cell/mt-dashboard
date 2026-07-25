# Editor Interactions — Behaviour Contract

This file defines how a professional layout editor should behave.
It describes the **behaviour contract**, not any specific implementation
library, framework, or source code.

---

## Selection

### Single selection
Clicking a visual selects it and deselects all others. The selected visual
shows resize handles and a highlight border.

### Additive selection (Shift-click)
Shift-clicking an unselected visual adds it to the current selection.
Shift-clicking a selected visual removes it from the selection.

### Toggle selection (Ctrl/Cmd-click)
Ctrl or Cmd-click behaves identically to Shift-click.

### Drag-selection rectangle
Pressing and dragging on the canvas background draws a selection rectangle.
All visuals whose bounding box intersects the rectangle are added to the selection.
A drag that produces a rectangle smaller than a minimum threshold (e.g. 4 × 4 px)
is treated as an accidental gesture and produces no selection change.

### Clear selection
Clicking the canvas background (outside all visuals) clears the selection.
Pressing Escape also clears the selection.

### Select all
Ctrl/Cmd-A selects all visuals on the current page.

---

## Movement

### Mouse drag
Dragging a selected visual (or any visual within a multi-selection) moves
all selected visuals by the same delta.

### Snap to grid
When snap-to-grid is enabled, dragged positions are rounded to the nearest
grid multiple. Snap applies to the top-left corner of the visual.

### Keyboard movement
Arrow keys move selected visuals by one grid unit in the pressed direction.
Shift + Arrow keys move selected visuals by a larger step (e.g. 10 grid units).

### Boundary constraint
Visuals cannot be moved to negative coordinates. Movement that would push a
visual beyond x=0 or y=0 is clamped at zero. Moving beyond the canvas bottom
or right edge is allowed but produces a validation warning.

---

## Editing operations

### Delete
Delete or Backspace removes all selected visuals. This action is undoable.

### Duplicate
Ctrl/Cmd-D creates copies of all selected visuals, offset by a small fixed
delta (e.g. 10 px right and 10 px down). New visuals receive new unique IDs.

### Copy / Paste
Ctrl/Cmd-C copies selected visuals to an in-memory clipboard.
Ctrl/Cmd-V pastes the clipboard contents as new visuals with new unique IDs,
offset by a small fixed delta from the original positions.

### Lock / Unlock
A locked visual cannot be moved, resized, or deleted through normal gestures.
It remains visible and selectable for inspection. A locked visual can only be
unlocked through an explicit unlock action.

### Show / Hide
Hidden visuals are invisible at runtime but remain in the specification.
They are shown in the editor with reduced opacity so designers can see and
manage them. Hidden status is toggled explicitly; it does not affect position.

---

## Multi-selection operations

When two or more visuals are selected:

### Align
- **Align left**: set all selected x to the minimum x in the selection.
- **Align right**: set all selected x + width to the maximum x + width.
- **Align top**: set all selected y to the minimum y.
- **Align bottom**: set all selected y + height to the maximum y + height.
- **Align centre (horizontal)**: centre all visuals on the horizontal midpoint of the selection bounding box.
- **Align middle (vertical)**: centre all visuals on the vertical midpoint.

### Distribute
- **Distribute horizontally**: spread visuals evenly across the horizontal span of the selection. Leftmost and rightmost visuals do not move.
- **Distribute vertically**: spread visuals evenly across the vertical span. Top and bottom visuals do not move.

### Z-order
- **Bring forward**: increase the zIndex of selected visuals by 1 relative to the visual immediately above.
- **Send backward**: decrease the zIndex by 1 relative to the visual immediately below.
- Clamped at 0 (minimum) and 9999 (maximum).

### Group / Ungroup
- **Group**: create a VisualGroup with a generated ID containing the selected visual IDs. Groups move together.
- **Ungroup**: remove the group; visuals become independent. Visual positions and sizes are unchanged.

---

## Resize

Resize handles appear on all four corners and four edge midpoints of a selected visual.
Dragging a handle changes width, height, and/or position according to which handle is used.
Minimum size: 10 × 10 px.
Snap-to-grid applies to resize as well as movement.
Aspect ratio is not locked by default; Shift-drag locks the aspect ratio.

---

## Undo / Redo

Every mutating action (add, delete, move, resize, format change, group/ungroup)
creates a history entry.

**History must not record**:
- Continuous pointer movement events during a drag
- Intermediate positions during a resize
- Autosave events
- Selection changes (these are non-destructive)

A single drag-and-release creates exactly one history entry at the moment of release.

Maximum history depth: 100 entries. When the limit is reached, the oldest entry
is discarded (FIFO).

Undo: Ctrl/Cmd-Z steps back one history entry.
Redo: Ctrl/Cmd-Y or Ctrl/Cmd-Shift-Z steps forward.
Redo history is cleared when a new mutation is made after an undo.

---

## Autosave

The editor autosaves the current layout to local storage after a debounce
period (e.g. 2 seconds) following the last mutation.

Before saving, the layout JSON is scanned for secret patterns. If a secret
pattern is detected, the save is aborted and the user is notified.

On startup, if a saved state exists:
- Its schema version is compared to the current schema version.
- If the schema is current, the user is offered a choice to restore it or start fresh.
- If the schema version is older, migration is attempted before offering restore.
- If migration fails, the saved state is discarded and the user is notified.
- If the saved state fails validation, it is discarded safely — never partially applied.

---

## Mode switching

The editor supports at least three interaction modes:

| Mode | Behaviour |
|------|-----------|
| Select | Default; click and drag to select and move visuals |
| Add | Clicking the canvas inserts a new visual of the chosen type at the click position |
| Pan | Click and drag moves the viewport; visuals are not selected or moved |

Switching modes clears any in-progress gesture cleanly.
