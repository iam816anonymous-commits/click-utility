# 🎨 Palette's UX Journal

## 2025-02-13 - Safe Destructive Actions & Accessible Control Prompts
**Learning:** Destructive operations (such as deleting registered rules/macros or template image assets) require robust confirmation layers and clear visual hierarchy. Immediate deletion without confirmation causes high user frustration from accidental clicks. Similarly, native desktop PySide6 buttons containing only icon glyphs (like trash cans or action symbols) are completely invisible to screen readers without an explicit accessible name (`setAccessibleName`) and lack contextual hints without a hover tooltip (`setToolTip`).
**Action:** Always wrap delete and other destructive triggers in an asynchronous confirmation prompt (`QMessageBox.question` run safely outside thread locks) and provide explicit accessibility attributes (`setAccessibleName` / `setToolTip`) on all desktop buttons.
