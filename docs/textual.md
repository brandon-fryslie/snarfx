# SnarfX Textual Integration

Reactive state management for [Textual](https://textual.textualize.io/) TUI applications. This module bridges SnarfX observables to Textual's widget tree with thread safety, lifecycle guards, and error handling.

```
pip install snarfx[textual]
```

## The Problem

Connecting reactive state to a Textual UI involves three concerns that the core SnarfX library intentionally does not address:

1. **Thread marshaling.** Background threads (polling, I/O workers) that mutate observables must marshal widget updates to the main thread via `app.call_from_thread`.

2. **Widget lifecycle.** Reactions that query the widget tree will raise `NoMatches` during screen transitions, widget replacement, or before the app is fully mounted. These must be caught, not propagated.

3. **Hot-reload pauses.** During widget replacement (e.g., Textual's dev mode), the widget tree is temporarily in an invalid state. Reactions must be suppressed during this window.

`snarfx.textual` handles all three at a single enforcement point.

## Usage

```python
from snarfx import Observable
import snarfx.textual as stx
```

### autorun

Runs the function immediately, then re-runs whenever any observable it reads changes. Widget queries are guarded against lifecycle issues.

```python
class DashboardScreen(Screen):
    def on_mount(self):
        self.status = Observable("connecting...")

        self._reaction = stx.autorun(self.app, self._update_status)

    def _update_status(self):
        label = self.query_one("#status", Label)
        label.update(self.status.get())

    def on_unmount(self):
        self._reaction.dispose()
```

What happens under the hood:

- If the app is not running or is paused, the callback is silently skipped.
- If the callback raises `NoMatches` (widget not yet mounted or already removed), it is caught.
- If the callback fires from a background thread, it is marshaled to the main thread via `app.call_from_thread`.

### reaction

Separates data selection from the UI effect. The effect only fires when the selected value actually changes.

```python
class ConnectionPanel(Screen):
    def on_mount(self):
        self._reaction = stx.reaction(
            self.app,
            lambda: self.connection_state.get(),
            self._on_connection_change,
        )

    def _on_connection_change(self, state):
        indicator = self.query_one("#indicator", Static)
        indicator.update(f"Status: {state}")
        indicator.styles.color = "green" if state == "connected" else "red"

    def on_unmount(self):
        self._reaction.dispose()
```

The `fire_immediately` keyword argument works as in core SnarfX:

```python
stx.reaction(
    self.app,
    lambda: config.get("theme"),
    self._apply_theme,
    fire_immediately=True,  # apply current theme on mount
)
```

### pause

Suppresses all guarded reactions during widget replacement or screen transitions. Use this when you know the widget tree will be temporarily invalid.

```python
async def replace_panel(self):
    with stx.pause(self.app):
        await self.query_one("#panel").remove()
        await self.mount(NewPanel(), before="#footer")
    # reactions resume here, widget tree is valid again
```

Multiple apps are supported (keyed by `id(app)`), so `pause` is safe in test environments with concurrent app instances.

### is_safe

Low-level check used internally by `autorun` and `reaction`. Returns `True` when the app is running and not paused. Available if you need to build custom guards.

```python
if stx.is_safe(app):
    widget = app.query_one("#target", Label)
    widget.update(new_value)
```

## Combining with watch and set_scheduler

For background I/O, combine `snarfx.watch` with `set_scheduler` to automatically marshal observable mutations to the Textual main thread.

```python
from snarfx import Observable, watch, set_scheduler
import snarfx.textual as stx

class MonitorApp(App):
    def on_mount(self):
        set_scheduler(self.call_from_thread)

        self.cpu_usage = Observable(0.0)
        self.mem_usage = Observable(0.0)

        # Background polling -- .set() auto-marshals to main thread
        self._watcher = watch(self._poll_system_stats)

        # UI reactions -- guarded against lifecycle issues
        stx.autorun(self.app, self._update_cpu_display)
        stx.autorun(self.app, self._update_mem_display)

    def _poll_system_stats(self):
        while True:
            self.cpu_usage.set(read_cpu())
            self.mem_usage.set(read_mem())
            time.sleep(1)

    def _update_cpu_display(self):
        self.query_one("#cpu", Label).update(f"CPU: {self.cpu_usage.get():.1f}%")

    def _update_mem_display(self):
        self.query_one("#mem", Label).update(f"MEM: {self.mem_usage.get():.1f}%")
```

## Combining with Store

`Store` and `HotReloadStore` provide schema-based state with lifecycle management. This pairs well with Textual screens that need structured state.

```python
from snarfx import Store
import snarfx.textual as stx

class SettingsScreen(Screen):
    def on_mount(self):
        self.store = Store(
            schema={"volume": 50, "brightness": 80, "notifications": True},
        )

        self._reactions = [
            stx.reaction(
                self.app,
                lambda: self.store.get("volume"),
                self._update_volume_slider,
            ),
            stx.reaction(
                self.app,
                lambda: self.store.get("brightness"),
                self._update_brightness_slider,
            ),
        ]

    def _update_volume_slider(self, value):
        self.query_one("#volume-slider", ProgressBar).update(progress=value)

    def _update_brightness_slider(self, value):
        self.query_one("#brightness-slider", ProgressBar).update(progress=value)

    def on_unmount(self):
        for r in self._reactions:
            r.dispose()
        self.store.dispose()
```

## API Reference

All functions are imported from `snarfx.textual`:

```python
import snarfx.textual as stx
```

| Function | Signature | Description |
|---|---|---|
| `autorun` | `(app, fn) -> Reaction` | Guarded autorun tied to app lifecycle |
| `reaction` | `(app, data_fn, effect_fn, *, fire_immediately=False) -> Reaction` | Guarded reaction tied to app lifecycle |
| `pause` | `(app) -> ContextManager` | Suppress reactions during widget replacement |
| `is_safe` | `(app) -> bool` | Check if app is running and not paused |

All guarded functions:

- Skip execution when the app is not running
- Skip execution during `pause()` blocks
- Catch `NoMatches` from widget queries
- Marshal cross-thread calls via `app.call_from_thread`

## Requirements

- `snarfx`
- `textual`

Install both with `pip install snarfx[textual]`.
