# Playground design specification

The working concept is `playground-concept.png`, generated with the built-in Image
Gen tool for a full 1536 × 1024 primary screen. It is a design reference, not the UI.

Direction: quiet paper surface, forest-green editor, serif editorial typography,
lime keywords, fine rules, and an open two-pane workspace. No imagery or decorative
brand symbol. All controls and text are native HTML. React/Vite builds a local bundle
served by the same Python process as the interpreter; the delivered bundle runs offline.

Tokens: background #fafaf7; ink #102b26; editor #14332e; accent #d9f085;
muted #627174; border #cdd5d1. Georgia/serif for title and wordmark; system sans for
controls/body; ui-monospace for code/data. Desktop content gutter 3vw; top bar 68px;
title 56px at concept width; workspace approximately 63% editor / 37% preview;
10px outer radius; 1px dividers. Compact screens stack editor and preview.

Allowed primary copy: ZenSigil; Playground; Language guide; v0.1.0 · experimental;
Small rules. Clear intent.; Write a rule. Preview what it proposes.; Example;
Restock review; Synthetic sample data; Run preview; restock.zs; ZenSigil;
Preview; Ready for review; 2 proposals · 1 note; reorder; sku; quantity;
target_days; A17; 105; 30; B24; 54; Skipped D09: sales missing;
Sample data; 5 inventory items; Nothing is sent or purchased. This is a local
preview.; Download preview.

Necessary functional extensions: initial/busy/error/stale states, all ten example
choices, editable JSON, a guide panel, line-numbered diagnostics, deduplication
counts and download-disabled state. The example code includes optional-field and
nonpositive-sales handling added after the concept. Use singular/plural counts.
The screenshot's code is conceptual; the working .zs file is authoritative.

Components: App owns request/edit state; CodeEditor owns highlighting/scroll sync;
Preview owns proposal/note/error presentation; Guide owns a small reference view.
Primary flow: choose sample → edit code or JSON → run → review output or diagnostics
→ download the current successful preview. Editing immediately invalidates the old
preview. Switching examples resets the draft and loads that example's input.

Image Gen brief: Full desktop primary screen for a local readable-language playground,
paper white and forest ink, serif wordmark/title, native code editor and preview rows,
example selector, run button, sample JSON fold, preview-only notice and JSON download.
No marketing sections, illustrations, fake metrics or extra navigation.

## 0.2 functional extension

The existing palette, typography and editor/preview layout remain in use. The
requested program library, dirty-change choice, input-contract panel, validation
paths and explanation/evidence rendering extend the original screen. The intro
now describes a language for programs broadly. Version is 0.2.0; saved drafts
recover after reload. Desktop/mobile behavior is verified against the implemented
flows, with the original image retained as a historical design reference.
