"""
gui.py
------
Complete Tkinter GUI for the AI Exercise Planner.

Pages (frames):
  - Dashboard
  - Exercise Library
  - Weekly Planner
  - AI Workout Assistant
  - Quick Workout
  - Progress
  - Settings

Navigation is handled by a left-side button bar.
Each page is a tk.Frame stacked in the content area.
"""

import logging
import random
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Optional

import config
import exercise as ex_module
import granite_ai
import planner as plan_module
import progress as prog_module
import storage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette and fonts
# ---------------------------------------------------------------------------
CLR_BG = "#F0F4F8"
CLR_SIDEBAR = "#1E293B"
CLR_SIDEBAR_HOVER = "#334155"
CLR_SIDEBAR_ACTIVE = "#3B82F6"
CLR_WHITE = "#FFFFFF"
CLR_ACCENT = "#3B82F6"
CLR_SUCCESS = "#22C55E"
CLR_DANGER = "#EF4444"
CLR_WARNING = "#F59E0B"
CLR_TEXT = "#1E293B"
CLR_MUTED = "#64748B"
CLR_BORDER = "#CBD5E1"
CLR_CARD = "#FFFFFF"

FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_HEADING = ("Segoe UI", 14, "bold")
FONT_SUBHEADING = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 9)

SIDEBAR_W = 200


# ---------------------------------------------------------------------------
# Utility widgets
# ---------------------------------------------------------------------------

def _scrolled_frame(parent: tk.Widget) -> tuple[tk.Frame, tk.Canvas]:
    """Return (inner_frame, canvas) – a vertically-scrollable container."""
    canvas = tk.Canvas(parent, bg=CLR_BG, highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=CLR_BG)
    inner_win = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_configure(event: tk.Event) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(inner_win, width=canvas.winfo_width())

    inner.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(inner_win, width=canvas.winfo_width()))
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def _on_mousewheel(event: tk.Event) -> None:
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    return inner, canvas


def _card(parent: tk.Widget, **kwargs) -> tk.Frame:
    """Return a white rounded-looking card frame."""
    defaults = {"bg": CLR_CARD, "relief": "flat", "bd": 1, "padx": 12, "pady": 12}
    defaults.update(kwargs)
    f = tk.Frame(parent, **defaults)
    f.configure(highlightbackground=CLR_BORDER, highlightthickness=1)
    return f


def _label(parent: tk.Widget, text: str, **kwargs) -> tk.Label:
    defaults = {"bg": CLR_BG, "fg": CLR_TEXT, "font": FONT_BODY}
    defaults.update(kwargs)
    return tk.Label(parent, text=text, **defaults)


def _btn(parent: tk.Widget, text: str, command=None, color: str = CLR_ACCENT, **kwargs) -> tk.Button:
    defaults = {
        "bg": color, "fg": CLR_WHITE, "font": FONT_BODY,
        "relief": "flat", "cursor": "hand2", "padx": 10, "pady": 5,
        "activebackground": CLR_SIDEBAR_HOVER, "activeforeground": CLR_WHITE,
        "command": command,
    }
    defaults.update(kwargs)
    return tk.Button(parent, text=text, **defaults)


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------

class App(tk.Tk):
    """Root window – owns the data store and all pages."""

    def __init__(self) -> None:
        super().__init__()
        self.title(config.APP_TITLE)
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(bg=CLR_BG)

        # Ensure data file exists.
        storage.ensure_data_file()

        # Load data into memory.
        self.data: dict[str, Any] = storage.load_data()

        self._build_layout()
        self._show_page("dashboard")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        # Sidebar
        self.sidebar = tk.Frame(self, bg=CLR_SIDEBAR, width=SIDEBAR_W)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # App title in sidebar
        tk.Label(
            self.sidebar,
            text="🏋  AI Exercise\nPlanner",
            bg=CLR_SIDEBAR,
            fg=CLR_WHITE,
            font=("Segoe UI", 12, "bold"),
            justify="center",
            pady=20,
        ).pack(fill="x")

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=10, pady=4)

        # Navigation buttons
        self._nav_buttons: dict[str, tk.Button] = {}
        nav_items = [
            ("dashboard",   "🏠  Dashboard"),
            ("exercises",   "📋  Exercise Library"),
            ("planner",     "📅  Weekly Planner"),
            ("ai",          "🤖  AI Workout Assistant"),
            ("quick",       "⚡  Quick Workout"),
            ("progress",    "📊  Progress"),
            ("settings",    "⚙️  Settings"),
        ]
        for page_id, label in nav_items:
            btn = tk.Button(
                self.sidebar,
                text=label,
                bg=CLR_SIDEBAR,
                fg=CLR_WHITE,
                font=FONT_BODY,
                relief="flat",
                anchor="w",
                padx=16,
                pady=10,
                cursor="hand2",
                activebackground=CLR_SIDEBAR_HOVER,
                activeforeground=CLR_WHITE,
                command=lambda pid=page_id: self._show_page(pid),
            )
            btn.pack(fill="x")
            self._nav_buttons[page_id] = btn

        # Spacer + Exit at bottom
        tk.Frame(self.sidebar, bg=CLR_SIDEBAR).pack(fill="both", expand=True)
        tk.Button(
            self.sidebar,
            text="🚪  Exit",
            bg=CLR_SIDEBAR,
            fg="#FDA4AF",
            font=FONT_BODY,
            relief="flat",
            anchor="w",
            padx=16, pady=10,
            cursor="hand2",
            activebackground=CLR_SIDEBAR_HOVER,
            activeforeground=CLR_WHITE,
            command=self._on_exit,
        ).pack(fill="x", side="bottom")

        # Content area
        self.content = tk.Frame(self, bg=CLR_BG)
        self.content.pack(side="left", fill="both", expand=True)

        # Build all pages
        self._pages: dict[str, tk.Frame] = {
            "dashboard":  DashboardPage(self.content, self),
            "exercises":  ExerciseLibraryPage(self.content, self),
            "planner":    WeeklyPlannerPage(self.content, self),
            "ai":         AIAssistantPage(self.content, self),
            "quick":      QuickWorkoutPage(self.content, self),
            "progress":   ProgressPage(self.content, self),
            "settings":   SettingsPage(self.content, self),
        }
        for page in self._pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _show_page(self, page_id: str) -> None:
        for pid, btn in self._nav_buttons.items():
            btn.configure(bg=CLR_SIDEBAR_ACTIVE if pid == page_id else CLR_SIDEBAR)
        page = self._pages.get(page_id)
        if page:
            page.lift()
            page.on_show()  # type: ignore[attr-defined]

    def save(self) -> None:
        """Persist in-memory data to disk."""
        if not storage.save_data(self.data):
            messagebox.showwarning(
                "Save Error",
                "Could not save data to disk.\n"
                "Check that you have write access to the application folder.",
            )

    def _on_exit(self) -> None:
        self.save()
        self.destroy()


# ---------------------------------------------------------------------------
# Base page
# ---------------------------------------------------------------------------

class BasePage(tk.Frame):
    """All pages inherit from this class."""

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, bg=CLR_BG)
        self.app = app

    def on_show(self) -> None:
        """Called every time this page is shown. Override as needed."""
        pass

    def _page_title(self, text: str) -> None:
        tk.Label(
            self, text=text, bg=CLR_BG, fg=CLR_TEXT,
            font=FONT_TITLE, pady=16, padx=20, anchor="w",
        ).pack(fill="x")


# ===========================================================================
# DASHBOARD
# ===========================================================================

class DashboardPage(BasePage):

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, app)
        self._build()

    def _build(self) -> None:
        self._page_title(f"Welcome to {config.APP_TITLE}")
        self._stats_frame = tk.Frame(self, bg=CLR_BG, padx=20)
        self._stats_frame.pack(fill="x")

        # --- Stat cards (populated in on_show) ---
        self._stat_vars = {
            "exercises":  tk.StringVar(value="0"),
            "planned":    tk.StringVar(value="0"),
            "completed":  tk.StringVar(value="0"),
            "pct":        tk.StringVar(value="0%"),
        }
        labels = [
            ("exercises",  "Exercises in Library", CLR_ACCENT),
            ("planned",    "Exercises This Week",  CLR_WARNING),
            ("completed",  "Completed This Week",  CLR_SUCCESS),
            ("pct",        "Completion Rate",      "#8B5CF6"),
        ]
        for i, (key, title, color) in enumerate(labels):
            card = _card(self._stats_frame)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            self._stats_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=CLR_CARD, fg=CLR_MUTED, font=FONT_SMALL).pack(anchor="w")
            tk.Label(
                card, textvariable=self._stat_vars[key],
                bg=CLR_CARD, fg=color, font=("Segoe UI", 24, "bold")
            ).pack(anchor="w", pady=(4, 0))

        # --- Quick-action buttons ---
        qa = tk.Frame(self, bg=CLR_BG, padx=20, pady=8)
        qa.pack(fill="x")
        tk.Label(qa, text="Quick Actions", bg=CLR_BG, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w", pady=(0, 6))

        btn_row = tk.Frame(qa, bg=CLR_BG)
        btn_row.pack(fill="x")
        actions = [
            ("➕ Add Exercise",        lambda: self.app._show_page("exercises")),
            ("📅 Open Planner",        lambda: self.app._show_page("planner")),
            ("🤖 AI Workout",          lambda: self.app._show_page("ai")),
            ("⚡ Quick Workout",       lambda: self.app._show_page("quick")),
            ("📊 View Progress",       lambda: self.app._show_page("progress")),
        ]
        for text, cmd in actions:
            _btn(btn_row, text, cmd).pack(side="left", padx=4)

        # --- Today's plan summary ---
        summary_card = _card(self, padx=20, pady=14)
        summary_card.pack(fill="x", padx=28, pady=(8, 0))
        tk.Label(summary_card, text="Weekly Progress Overview", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w")
        self._progress_bar = ttk.Progressbar(summary_card, length=400, mode="determinate")
        self._progress_bar.pack(fill="x", pady=6)
        self._progress_lbl = tk.Label(summary_card, text="", bg=CLR_CARD, fg=CLR_MUTED, font=FONT_SMALL)
        self._progress_lbl.pack(anchor="w")

        # --- Disclaimer ---
        tk.Label(
            self, bg=CLR_BG, fg=CLR_MUTED, font=FONT_SMALL, wraplength=800,
            text=(
                "⚠️  AI-generated workout suggestions are for general fitness information "
                "only and are NOT a substitute for professional medical advice."
            ),
        ).pack(padx=20, pady=12, anchor="w")

    def on_show(self) -> None:
        total_ex = len(ex_module.get_all_exercises(self.app.data))
        p = prog_module.calculate_overall_progress(self.app.data)
        self._stat_vars["exercises"].set(str(total_ex))
        self._stat_vars["planned"].set(str(p["total"]))
        self._stat_vars["completed"].set(str(p["completed"]))
        self._stat_vars["pct"].set(f"{p['percentage']:.0f}%")
        self._progress_bar["value"] = p["percentage"]
        self._progress_lbl.configure(
            text=f"{p['completed']}/{p['total']} exercises completed  ·  "
                 f"{prog_module.format_duration(p['completed_duration_min'])} of "
                 f"{prog_module.format_duration(p['total_duration_min'])} done"
        )


# ===========================================================================
# EXERCISE LIBRARY
# ===========================================================================

class ExerciseLibraryPage(BasePage):

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, app)
        self._build()

    def _build(self) -> None:
        self._page_title("📋 Exercise Library")

        # --- Toolbar ---
        toolbar = tk.Frame(self, bg=CLR_BG, padx=20)
        toolbar.pack(fill="x", pady=(0, 6))

        tk.Label(toolbar, text="Search:", bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_list())
        search_entry = ttk.Entry(toolbar, textvariable=self._search_var, width=24)
        search_entry.pack(side="left", padx=(4, 12))

        tk.Label(toolbar, text="Category:", bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY).pack(side="left")
        self._cat_filter = tk.StringVar(value="All")
        cat_combo = ttk.Combobox(
            toolbar, textvariable=self._cat_filter,
            values=["All"] + config.EXERCISE_CATEGORIES, state="readonly", width=16
        )
        cat_combo.pack(side="left", padx=(4, 12))
        cat_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_list())

        _btn(toolbar, "➕ Add Exercise", self._open_add_dialog).pack(side="left", padx=4)
        _btn(toolbar, "✏️ Edit", self._open_edit_dialog, color="#8B5CF6").pack(side="left", padx=4)
        _btn(toolbar, "🗑️ Delete", self._delete_selected, color=CLR_DANGER).pack(side="left", padx=4)

        # --- Treeview ---
        tree_frame = tk.Frame(self, bg=CLR_BG, padx=20)
        tree_frame.pack(fill="both", expand=True)

        cols = ("Name", "Category", "Sets", "Reps", "Duration", "Difficulty", "Equipment")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        widths = {"Name": 200, "Category": 110, "Sets": 55, "Reps": 55, "Duration": 80, "Difficulty": 100, "Equipment": 130}
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=widths.get(col, 100), anchor="center")
        self._tree.column("Name", anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._tree.bind("<Double-1>", lambda _: self._open_edit_dialog())

        # Details panel
        detail_card = _card(self, padx=16, pady=12)
        detail_card.pack(fill="x", padx=20, pady=6)
        tk.Label(detail_card, text="Notes:", bg=CLR_CARD, fg=CLR_MUTED, font=FONT_SMALL).pack(anchor="w")
        self._detail_lbl = tk.Label(detail_card, text="Select an exercise to see details.", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_BODY, wraplength=700, justify="left")
        self._detail_lbl.pack(anchor="w")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def on_show(self) -> None:
        self._refresh_list()

    def _refresh_list(self) -> None:
        query = self._search_var.get().strip()
        cat = "" if self._cat_filter.get() == "All" else self._cat_filter.get()
        exercises = ex_module.search_exercises(self.app.data, query=query, category=cat)

        self._tree.delete(*self._tree.get_children())
        for e in exercises:
            dur = f"{e['duration']} min" if e.get("duration") else "—"
            self._tree.insert("", "end", iid=e["id"], values=(
                e.get("name", ""), e.get("category", ""), e.get("sets", 0),
                e.get("reps", 0), dur, e.get("difficulty", ""), e.get("equipment", ""),
            ))

    def _on_select(self, _event: tk.Event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        eid = sel[0]
        ex = ex_module.get_exercise_by_id(self.app.data, eid)
        if ex:
            notes = ex.get("notes") or "—"
            self._detail_lbl.configure(text=notes)

    def _selected_id(self) -> Optional[str]:
        sel = self._tree.selection()
        return sel[0] if sel else None

    # --- Add / Edit dialog ---

    def _open_add_dialog(self) -> None:
        self._open_exercise_dialog(None)

    def _open_edit_dialog(self) -> None:
        eid = self._selected_id()
        if not eid:
            messagebox.showinfo("No Selection", "Please select an exercise to edit.")
            return
        ex = ex_module.get_exercise_by_id(self.app.data, eid)
        self._open_exercise_dialog(ex)

    def _open_exercise_dialog(self, existing: Optional[dict[str, Any]]) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Edit Exercise" if existing else "Add Exercise")
        dlg.geometry("440x520")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg=CLR_BG)

        fields: dict[str, Any] = {}

        def row(label: str, widget_factory):
            r = tk.Frame(dlg, bg=CLR_BG)
            r.pack(fill="x", padx=20, pady=4)
            tk.Label(r, text=label, bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY, width=16, anchor="w").pack(side="left")
            w = widget_factory(r)
            w.pack(side="left", fill="x", expand=True)
            return w

        fields["name"] = row("Name *", lambda p: ttk.Entry(p))
        fields["category"] = row("Category", lambda p: ttk.Combobox(p, values=config.EXERCISE_CATEGORIES, state="readonly"))
        fields["difficulty"] = row("Difficulty", lambda p: ttk.Combobox(p, values=config.DIFFICULTY_LEVELS, state="readonly"))
        fields["equipment"] = row("Equipment", lambda p: ttk.Combobox(p, values=config.EQUIPMENT_OPTIONS, state="readonly"))
        fields["sets"] = row("Sets", lambda p: ttk.Entry(p))
        fields["reps"] = row("Reps", lambda p: ttk.Entry(p))
        fields["duration"] = row("Duration (min)", lambda p: ttk.Entry(p))

        tk.Label(dlg, text="Notes", bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY).pack(anchor="w", padx=20, pady=(6, 0))
        notes_txt = tk.Text(dlg, height=4, font=FONT_BODY, wrap="word")
        notes_txt.pack(fill="x", padx=20)

        # Pre-fill if editing
        if existing:
            fields["name"].insert(0, existing.get("name", ""))
            fields["category"].set(existing.get("category", config.EXERCISE_CATEGORIES[0]))
            fields["difficulty"].set(existing.get("difficulty", "Beginner"))
            fields["equipment"].set(existing.get("equipment", "No Equipment"))
            fields["sets"].insert(0, str(existing.get("sets", 3)))
            fields["reps"].insert(0, str(existing.get("reps", 10)))
            fields["duration"].insert(0, str(existing.get("duration", 0)))
            notes_txt.insert("1.0", existing.get("notes", ""))
        else:
            fields["category"].set(config.EXERCISE_CATEGORIES[0])
            fields["difficulty"].set("Beginner")
            fields["equipment"].set("No Equipment")
            fields["sets"].insert(0, "3")
            fields["reps"].insert(0, "10")
            fields["duration"].insert(0, "0")

        def _save() -> None:
            raw = {
                "name": fields["name"].get().strip(),
                "category": fields["category"].get(),
                "difficulty": fields["difficulty"].get(),
                "equipment": fields["equipment"].get(),
                "sets": fields["sets"].get().strip() or "0",
                "reps": fields["reps"].get().strip() or "0",
                "duration": fields["duration"].get().strip() or "0",
                "notes": notes_txt.get("1.0", "end-1c").strip(),
            }
            ok, err = ex_module.validate_exercise(raw)
            if not ok:
                messagebox.showerror("Validation Error", err, parent=dlg)
                return
            try:
                raw["sets"] = int(raw["sets"])
                raw["reps"] = int(raw["reps"])
                raw["duration"] = int(raw["duration"])
            except ValueError:
                messagebox.showerror("Validation Error", "Sets, reps, and duration must be whole numbers.", parent=dlg)
                return

            if existing:
                ex_module.update_exercise(self.app.data, existing["id"], raw)
            else:
                new_ex = ex_module.make_exercise(**raw)
                ex_module.add_exercise(self.app.data, new_ex)

            self.app.save()
            self._refresh_list()
            dlg.destroy()

        btn_row = tk.Frame(dlg, bg=CLR_BG)
        btn_row.pack(fill="x", padx=20, pady=10)
        _btn(btn_row, "Save", _save).pack(side="right", padx=4)
        _btn(btn_row, "Cancel", dlg.destroy, color=CLR_MUTED).pack(side="right", padx=4)

    def _delete_selected(self) -> None:
        eid = self._selected_id()
        if not eid:
            messagebox.showinfo("No Selection", "Please select an exercise to delete.")
            return
        ex = ex_module.get_exercise_by_id(self.app.data, eid)
        name = ex.get("name", "?") if ex else "?"
        if not messagebox.askyesno("Confirm Delete", f"Delete '{name}'?\nThis will also remove it from the weekly plan."):
            return
        ex_module.delete_exercise(self.app.data, eid)
        self.app.save()
        self._refresh_list()


# ===========================================================================
# WEEKLY PLANNER
# ===========================================================================

class WeeklyPlannerPage(BasePage):

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, app)
        self._selected_day = tk.StringVar(value="Monday")
        self._build()

    def _build(self) -> None:
        self._page_title("📅 Weekly Planner")

        # Day selector
        day_bar = tk.Frame(self, bg=CLR_BG, padx=20)
        day_bar.pack(fill="x", pady=(0, 6))
        for day in config.DAYS_OF_WEEK:
            rb = tk.Radiobutton(
                day_bar, text=day, variable=self._selected_day, value=day,
                bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY,
                activebackground=CLR_BG, selectcolor=CLR_ACCENT,
                command=self._refresh_day,
            )
            rb.pack(side="left", padx=4)

        # Toolbar
        toolbar = tk.Frame(self, bg=CLR_BG, padx=20)
        toolbar.pack(fill="x", pady=4)
        _btn(toolbar, "➕ Add Exercise to Day", self._add_exercise_to_day).pack(side="left", padx=4)
        _btn(toolbar, "✔ Toggle Completed", self._toggle_completed, color=CLR_SUCCESS).pack(side="left", padx=4)
        _btn(toolbar, "🗑️ Remove Entry", self._remove_entry, color=CLR_DANGER).pack(side="left", padx=4)
        _btn(toolbar, "🔄 Reset Week Completions", self._reset_all, color=CLR_WARNING).pack(side="right", padx=4)

        # Day plan treeview
        tree_frame = tk.Frame(self, bg=CLR_BG, padx=20)
        tree_frame.pack(fill="both", expand=True)

        cols = ("Exercise", "Sets", "Reps", "Duration", "Completed", "Notes")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        widths = {"Exercise": 220, "Sets": 55, "Reps": 55, "Duration": 90, "Completed": 90, "Notes": 250}
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=widths.get(col, 100), anchor="center")
        self._tree.column("Exercise", anchor="w")
        self._tree.column("Notes", anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Day summary label
        self._day_summary = tk.Label(self, text="", bg=CLR_BG, fg=CLR_MUTED, font=FONT_SMALL, padx=20)
        self._day_summary.pack(anchor="w", pady=(2, 8))

    def on_show(self) -> None:
        self._refresh_day()

    def _refresh_day(self) -> None:
        day = self._selected_day.get()
        entries = plan_module.get_day_entries(self.app.data, day)
        self._tree.delete(*self._tree.get_children())
        for e in entries:
            dur = f"{e['duration']} min" if e.get("duration") else "—"
            done = "✔ Done" if e.get("completed") else "—"
            self._tree.insert("", "end", iid=e["entry_id"], values=(
                e.get("exercise_name", ""), e.get("sets", 0), e.get("reps", 0),
                dur, done, e.get("notes", ""),
            ))
            if e.get("completed"):
                self._tree.item(e["entry_id"], tags=("done",))
        self._tree.tag_configure("done", foreground=CLR_SUCCESS)

        total = len(entries)
        completed = sum(1 for e in entries if e.get("completed"))
        self._day_summary.configure(
            text=f"{day}: {total} exercise(s) — {completed} completed"
        )

    def _selected_entry_id(self) -> Optional[str]:
        sel = self._tree.selection()
        return sel[0] if sel else None

    def _add_exercise_to_day(self) -> None:
        exercises = ex_module.get_all_exercises(self.app.data)
        if not exercises:
            messagebox.showinfo("No Exercises", "Add exercises to the library first.")
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"Add Exercise – {self._selected_day.get()}")
        dlg.geometry("500x460")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg=CLR_BG)

        tk.Label(dlg, text="Select Exercise:", bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY).pack(anchor="w", padx=20, pady=(14, 2))
        ex_names = [e["name"] for e in exercises]
        selected_ex = tk.StringVar(value=ex_names[0])
        cb = ttk.Combobox(dlg, textvariable=selected_ex, values=ex_names, state="readonly", width=40)
        cb.pack(padx=20, pady=2)

        def fields_row(label: str) -> ttk.Entry:
            r = tk.Frame(dlg, bg=CLR_BG)
            r.pack(fill="x", padx=20, pady=3)
            tk.Label(r, text=label, bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY, width=14, anchor="w").pack(side="left")
            e = ttk.Entry(r)
            e.pack(side="left", fill="x", expand=True)
            return e

        sets_e = fields_row("Sets (override):")
        reps_e = fields_row("Reps (override):")
        dur_e  = fields_row("Duration min (override):")

        tk.Label(dlg, text="Notes:", bg=CLR_BG, fg=CLR_TEXT, font=FONT_BODY).pack(anchor="w", padx=20, pady=(6, 0))
        notes_txt = tk.Text(dlg, height=3, font=FONT_BODY, wrap="word")
        notes_txt.pack(fill="x", padx=20)

        def _autofill(_event=None) -> None:
            ex_name = selected_ex.get()
            ex_obj = next((e for e in exercises if e["name"] == ex_name), None)
            if ex_obj:
                sets_e.delete(0, "end"); sets_e.insert(0, str(ex_obj.get("sets", 0)))
                reps_e.delete(0, "end"); reps_e.insert(0, str(ex_obj.get("reps", 0)))
                dur_e.delete(0, "end");  dur_e.insert(0, str(ex_obj.get("duration", 0)))
        cb.bind("<<ComboboxSelected>>", _autofill)
        _autofill()

        def _add() -> None:
            ex_name = selected_ex.get()
            ex_obj = next((e for e in exercises if e["name"] == ex_name), None)
            if not ex_obj:
                messagebox.showerror("Error", "Selected exercise not found.", parent=dlg)
                return
            try:
                sets = int(sets_e.get() or "0")
                reps = int(reps_e.get() or "0")
                dur  = int(dur_e.get() or "0")
            except ValueError:
                messagebox.showerror("Error", "Sets, reps, duration must be whole numbers.", parent=dlg)
                return
            entry = plan_module.make_plan_entry(
                exercise_id=ex_obj["id"],
                exercise_name=ex_obj["name"],
                sets=sets, reps=reps, duration=dur,
                notes=notes_txt.get("1.0", "end-1c").strip(),
            )
            plan_module.add_entry_to_day(self.app.data, self._selected_day.get(), entry)
            self.app.save()
            self._refresh_day()
            dlg.destroy()

        btn_row = tk.Frame(dlg, bg=CLR_BG)
        btn_row.pack(fill="x", padx=20, pady=10)
        _btn(btn_row, "Add to Day", _add).pack(side="right", padx=4)
        _btn(btn_row, "Cancel", dlg.destroy, color=CLR_MUTED).pack(side="right", padx=4)

    def _toggle_completed(self) -> None:
        eid = self._selected_entry_id()
        if not eid:
            messagebox.showinfo("No Selection", "Select an entry to toggle.")
            return
        plan_module.toggle_entry_completed(self.app.data, self._selected_day.get(), eid)
        self.app.save()
        self._refresh_day()

    def _remove_entry(self) -> None:
        eid = self._selected_entry_id()
        if not eid:
            messagebox.showinfo("No Selection", "Select an entry to remove.")
            return
        if not messagebox.askyesno("Confirm", "Remove this entry from the plan?"):
            return
        plan_module.remove_entry_from_day(self.app.data, self._selected_day.get(), eid)
        self.app.save()
        self._refresh_day()

    def _reset_all(self) -> None:
        if not messagebox.askyesno("Reset", "Mark all exercises as not completed?"):
            return
        plan_module.reset_all_completions(self.app.data)
        self.app.save()
        self._refresh_day()


# ===========================================================================
# AI WORKOUT ASSISTANT
# ===========================================================================

class AIAssistantPage(BasePage):

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, app)
        self._last_plan: Optional[dict[str, Any]] = None
        self._last_raw: str = ""
        self._build()

    def _build(self) -> None:
        self._page_title("🤖 AI Workout Assistant")

        # --- Configuration warning banner (shown when Granite not configured) ---
        self._config_banner = tk.Frame(self, bg="#FEF3C7", bd=1, relief="flat",
                                        highlightbackground=CLR_WARNING, highlightthickness=1)
        self._config_lbl = tk.Label(
            self._config_banner,
            text="", bg="#FEF3C7", fg="#92400E",
            font=FONT_SMALL, wraplength=800, justify="left", padx=12, pady=8,
        )
        self._config_lbl.pack(anchor="w")

        # Two-column layout: inputs left, output right
        main = tk.Frame(self, bg=CLR_BG)
        main.pack(fill="both", expand=True, padx=20, pady=6)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # --- LEFT: input panel ---
        left = _card(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(left, text="Workout Preferences", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w", pady=(0, 8))

        def field(lbl: str, widget_factory) -> Any:
            r = tk.Frame(left, bg=CLR_CARD)
            r.pack(fill="x", pady=3)
            tk.Label(r, text=lbl, bg=CLR_CARD, fg=CLR_TEXT, font=FONT_BODY, width=20, anchor="w").pack(side="left")
            w = widget_factory(r)
            w.pack(side="left", fill="x", expand=True)
            return w

        self._goal_var = tk.StringVar(value=config.FITNESS_GOALS[0])
        field("Fitness Goal:", lambda p: ttk.Combobox(p, textvariable=self._goal_var, values=config.FITNESS_GOALS, state="readonly"))

        self._exp_var = tk.StringVar(value="Beginner")
        field("Experience Level:", lambda p: ttk.Combobox(p, textvariable=self._exp_var, values=config.EXPERIENCE_LEVELS, state="readonly"))

        self._days_var = tk.StringVar(value="3")
        days_entry = field("Days per Week (1-7):", lambda p: ttk.Entry(p, textvariable=self._days_var, width=6))

        self._dur_var = tk.StringVar(value="30")
        field("Session Duration (min):", lambda p: ttk.Entry(p, textvariable=self._dur_var, width=6))

        self._equip_var = tk.StringVar(value="No Equipment")
        field("Equipment:", lambda p: ttk.Combobox(p, textvariable=self._equip_var, values=config.EQUIPMENT_OPTIONS, state="readonly"))

        tk.Label(left, text="Additional Instructions:", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_BODY).pack(anchor="w", pady=(8, 2))
        self._notes_txt = tk.Text(left, height=5, font=FONT_BODY, wrap="word", width=30)
        self._notes_txt.pack(fill="x")
        self._notes_txt.insert("1.0", "e.g. Avoid jumping exercises, focus on upper body")

        self._gen_btn = _btn(left, "🤖 Generate AI Workout Plan", self._generate, color=CLR_ACCENT)
        self._gen_btn.pack(fill="x", pady=(12, 0))

        self._status_lbl = tk.Label(left, text="", bg=CLR_CARD, fg=CLR_MUTED, font=FONT_SMALL, wraplength=260, justify="left")
        self._status_lbl.pack(anchor="w", pady=4)

        # Disclaimer
        tk.Label(
            left, bg=CLR_CARD, fg=CLR_MUTED, font=FONT_SMALL, wraplength=260, justify="left",
            text="⚠️ AI suggestions are for general fitness information only. Consult a healthcare professional before starting any exercise programme.",
        ).pack(anchor="w", pady=6)

        # --- RIGHT: output panel ---
        right = _card(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        out_toolbar = tk.Frame(right, bg=CLR_CARD)
        out_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(out_toolbar, text="Generated Workout Plan", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(side="left")
        self._save_btn = _btn(out_toolbar, "💾 Save Plan", self._save_plan, color=CLR_SUCCESS)
        self._save_btn.pack(side="right", padx=4)
        self._save_btn.configure(state="disabled")
        self._add_to_planner_btn = _btn(out_toolbar, "📅 Add to Weekly Planner", self._add_to_planner, color="#8B5CF6")
        self._add_to_planner_btn.pack(side="right", padx=4)
        self._add_to_planner_btn.configure(state="disabled")

        self._output_txt = tk.Text(
            right, font=FONT_MONO, wrap="word",
            bg="#F8FAFC", fg=CLR_TEXT, relief="flat",
            state="disabled",
        )
        self._output_txt.grid(row=1, column=0, sticky="nsew")
        out_vsb = ttk.Scrollbar(right, orient="vertical", command=self._output_txt.yview)
        self._output_txt.configure(yscrollcommand=out_vsb.set)
        out_vsb.grid(row=1, column=1, sticky="ns")

        self._output_txt.tag_configure("heading", font=("Segoe UI", 11, "bold"), foreground=CLR_ACCENT)
        self._output_txt.tag_configure("exercise", font=("Segoe UI", 10, "bold"))
        self._output_txt.tag_configure("detail", font=FONT_BODY, foreground=CLR_MUTED)
        self._output_txt.tag_configure("warning", foreground=CLR_WARNING)
        self._output_txt.tag_configure("error", foreground=CLR_DANGER)

    def on_show(self) -> None:
        if config.granite_is_configured():
            self._config_banner.pack_forget()
        else:
            self._config_banner.pack(fill="x", padx=20, pady=(0, 6), before=self._output_txt.master)
            self._config_lbl.configure(
                text=(
                    "⚠️  IBM Granite is not configured.  Set IBM_GRANITE_API_KEY and "
                    "IBM_WATSONX_PROJECT_ID in your .env file to enable AI features.  "
                    "See README.md for instructions."
                )
            )

    def _validate_inputs(self) -> Optional[dict[str, Any]]:
        goal = self._goal_var.get().strip()
        exp  = self._exp_var.get().strip()
        equip = self._equip_var.get().strip()

        try:
            days = int(self._days_var.get())
            if not 1 <= days <= 7:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Days per week must be a whole number between 1 and 7.")
            return None

        try:
            dur = int(self._dur_var.get())
            if not 15 <= dur <= 120:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Session duration must be between 15 and 120 minutes.")
            return None

        if not goal:
            messagebox.showerror("Invalid Input", "Please select a fitness goal.")
            return None
        if not exp:
            messagebox.showerror("Invalid Input", "Please select an experience level.")
            return None

        notes = self._notes_txt.get("1.0", "end-1c").strip()
        # Remove placeholder hint if still present
        if notes == "e.g. Avoid jumping exercises, focus on upper body":
            notes = ""

        return {
            "goal": goal, "experience": exp, "days_per_week": days,
            "duration_min": dur, "equipment": equip, "extra_notes": notes,
        }

    def _generate(self) -> None:
        user_req = self._validate_inputs()
        if not user_req:
            return

        self._gen_btn.configure(state="disabled", text="⏳ Generating…")
        self._status_lbl.configure(text="Contacting IBM Granite…")
        self._set_output("⏳ Sending your request to IBM Granite...\n\nThis may take up to 60 seconds.", tag="detail")
        self._save_btn.configure(state="disabled")
        self._add_to_planner_btn.configure(state="disabled")

        def _worker() -> None:
            result = granite_ai.generate_workout_plan(user_req)
            self.after(0, lambda: self._on_result(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_result(self, result: granite_ai.GraniteResponse) -> None:
        self._gen_btn.configure(state="normal", text="🤖 Generate AI Workout Plan")
        if result.success and result.plan:
            self._last_plan = result.plan
            self._last_raw = result.raw_text
            self._render_plan(result.plan)
            self._status_lbl.configure(text="✔ Plan generated successfully.", fg=CLR_SUCCESS)
            self._save_btn.configure(state="normal")
            self._add_to_planner_btn.configure(state="normal")
        else:
            self._last_plan = None
            self._last_raw = result.raw_text
            self._status_lbl.configure(text="❌ Generation failed.", fg=CLR_DANGER)

            msg = result.error_message or "Unknown error."
            self._set_output(f"❌ Error:\n\n{msg}", tag="error")
            if result.raw_text:
                self._append_output(f"\n\n--- Raw Response (for reference) ---\n{result.raw_text}", tag="detail")

    def _render_plan(self, plan: dict[str, Any]) -> None:
        self._clear_output()
        txt = self._output_txt
        txt.configure(state="normal")

        def h(t: str) -> None:
            txt.insert("end", t + "\n", "heading")

        def b(t: str) -> None:
            txt.insert("end", t + "\n", "exercise")

        def d(t: str) -> None:
            txt.insert("end", t + "\n", "detail")

        def nl() -> None:
            txt.insert("end", "\n")

        h(f"🎯 Goal: {plan.get('goal', '?')}  |  Experience: {plan.get('experience', '?')}")
        d(f"Days/week: {plan.get('days_per_week', '?')}  |  Duration: {plan.get('duration_min', '?')} min  |  Equipment: {plan.get('equipment', '?')}")
        nl()

        # Warm-up
        warm_up = plan.get("warm_up", {})
        if warm_up:
            h("🔥 Warm-Up")
            d(f"{warm_up.get('description', '—')}  ({warm_up.get('duration_min', 0)} min)")
            nl()

        # Schedule
        schedule = plan.get("schedule", [])
        if schedule:
            h("📅 Weekly Schedule")
            for day_block in schedule:
                day_name = day_block.get("day", "?")
                focus = day_block.get("focus", "")
                b(f"\n  {day_name}" + (f" – {focus}" if focus else ""))
                for ex in day_block.get("exercises", []):
                    sets_reps = ""
                    if ex.get("sets") and ex.get("reps"):
                        sets_reps = f"{ex['sets']} sets × {ex['reps']} reps"
                    elif ex.get("duration_min"):
                        sets_reps = f"{ex['duration_min']} min"
                    rest = f"  Rest: {ex['rest_sec']}s" if ex.get("rest_sec") else ""
                    txt.insert("end", f"    • {ex.get('name', '?')}", "exercise")
                    txt.insert("end", f"  [{sets_reps}{rest}]  [{ex.get('difficulty', '?')}]\n", "detail")
                    if ex.get("instructions"):
                        d(f"      ↳ {ex['instructions']}")
            nl()

        # Cool-down
        cool_down = plan.get("cool_down", {})
        if cool_down:
            h("❄️ Cool-Down")
            d(f"{cool_down.get('description', '—')}  ({cool_down.get('duration_min', 0)} min)")
            nl()

        # Recovery
        recovery = plan.get("recovery_recommendations", "")
        if recovery:
            h("💤 Recovery Recommendations")
            d(recovery)
            nl()

        # Disclaimer
        disclaimer = plan.get("_disclaimer", "")
        if disclaimer:
            txt.insert("end", f"\n⚠️  {disclaimer}\n", "warning")

        txt.configure(state="disabled")

    def _set_output(self, text: str, tag: str = "") -> None:
        self._clear_output()
        self._append_output(text, tag)

    def _append_output(self, text: str, tag: str = "") -> None:
        self._output_txt.configure(state="normal")
        self._output_txt.insert("end", text, tag)
        self._output_txt.configure(state="disabled")

    def _clear_output(self) -> None:
        self._output_txt.configure(state="normal")
        self._output_txt.delete("1.0", "end")
        self._output_txt.configure(state="disabled")

    def _save_plan(self) -> None:
        if not self._last_plan:
            return
        plans = self.app.data.setdefault("ai_plans", [])
        import datetime
        entry = {
            "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "plan": self._last_plan,
            "raw": self._last_raw,
        }
        plans.append(entry)
        self.app.save()
        messagebox.showinfo("Saved", f"Plan saved. You have {len(plans)} saved AI plan(s).")

    def _add_to_planner(self) -> None:
        if not self._last_plan:
            return
        schedule = self._last_plan.get("schedule", [])
        if not schedule:
            messagebox.showinfo("No Schedule", "The plan does not contain a schedule.")
            return

        added_count = 0
        for day_block in schedule:
            raw_day = day_block.get("day", "")
            # Fuzzy-match day name (e.g. "Day 1 – Monday" → "Monday")
            matched_day = None
            for d in config.DAYS_OF_WEEK:
                if d.lower() in raw_day.lower():
                    matched_day = d
                    break
            if not matched_day:
                # Fallback: use positional day
                idx = schedule.index(day_block)
                if idx < len(config.DAYS_OF_WEEK):
                    matched_day = config.DAYS_OF_WEEK[idx]
                else:
                    continue

            for ex_item in day_block.get("exercises", []):
                name = ex_item.get("name", "AI Exercise")
                sets_val = ex_item.get("sets") or 0
                reps_val = ex_item.get("reps") or 0
                dur_val = ex_item.get("duration_min") or 0
                try:
                    sets_val = int(sets_val)
                    reps_val = int(reps_val)
                    dur_val  = int(dur_val)
                except (TypeError, ValueError):
                    sets_val = reps_val = dur_val = 0

                instructions = ex_item.get("instructions", "")

                entry = plan_module.make_plan_entry(
                    exercise_id="ai_generated",
                    exercise_name=name,
                    sets=sets_val, reps=reps_val, duration=dur_val,
                    notes=instructions,
                )
                plan_module.add_entry_to_day(self.app.data, matched_day, entry)
                added_count += 1

        self.app.save()
        messagebox.showinfo(
            "Added to Planner",
            f"Added {added_count} exercise(s) to the weekly planner.\n"
            "Open the Weekly Planner page to review.",
        )


# ===========================================================================
# QUICK WORKOUT
# ===========================================================================

class QuickWorkoutPage(BasePage):

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, app)
        self._workout_entries: list[dict[str, Any]] = []
        self._build()

    def _build(self) -> None:
        self._page_title("⚡ Quick Workout")

        top = tk.Frame(self, bg=CLR_BG, padx=20)
        top.pack(fill="x", pady=6)
        tk.Label(top, text="Randomly selects 3–5 exercises from your library.", bg=CLR_BG, fg=CLR_MUTED, font=FONT_BODY).pack(side="left")
        _btn(top, "🎲 Generate Quick Workout", self._generate).pack(side="left", padx=12)
        _btn(top, "✔ Mark All Completed", self._mark_all_done, color=CLR_SUCCESS).pack(side="left", padx=4)

        self._info_lbl = tk.Label(self, text="", bg=CLR_BG, fg=CLR_MUTED, font=FONT_BODY, padx=20)
        self._info_lbl.pack(anchor="w")

        tree_frame = tk.Frame(self, bg=CLR_BG, padx=20)
        tree_frame.pack(fill="both", expand=True)

        cols = ("Exercise", "Category", "Sets", "Reps", "Duration", "Difficulty", "Completed")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        widths = {"Exercise": 220, "Category": 110, "Sets": 55, "Reps": 55, "Duration": 90, "Difficulty": 100, "Completed": 90}
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=widths.get(col, 100), anchor="center")
        self._tree.column("Exercise", anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.tag_configure("done", foreground=CLR_SUCCESS)
        self._tree.bind("<Double-1>", lambda _: self._toggle_completed())

        btn_row = tk.Frame(self, bg=CLR_BG, padx=20, pady=6)
        btn_row.pack(fill="x")
        _btn(btn_row, "✔ Toggle Selected Completed", self._toggle_completed, color=CLR_SUCCESS).pack(side="left", padx=4)
        _btn(btn_row, "📅 Add to Today's Plan", self._add_to_plan, color="#8B5CF6").pack(side="left", padx=4)

    def on_show(self) -> None:
        self._generate()

    def _generate(self) -> None:
        all_ex = ex_module.get_all_exercises(self.app.data)
        self._workout_entries = []
        self._tree.delete(*self._tree.get_children())

        if len(all_ex) < 3:
            self._info_lbl.configure(
                text=f"⚠️ Not enough exercises in the library (need at least 3, have {len(all_ex)}).  "
                     "Add more exercises to use Quick Workout.",
                fg=CLR_WARNING,
            )
            return

        count = random.randint(3, min(5, len(all_ex)))
        selected = random.sample(all_ex, count)

        self._info_lbl.configure(text=f"Generated a quick workout with {count} exercises.  Double-click to toggle completion.", fg=CLR_MUTED)
        for e in selected:
            entry = dict(e)
            entry["completed"] = False
            self._workout_entries.append(entry)
            dur = f"{e['duration']} min" if e.get("duration") else "—"
            self._tree.insert("", "end", iid=e["id"], values=(
                e.get("name", ""), e.get("category", ""), e.get("sets", 0),
                e.get("reps", 0), dur, e.get("difficulty", ""), "—",
            ))

    def _toggle_completed(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select an exercise to toggle.")
            return
        eid = sel[0]
        for entry in self._workout_entries:
            if entry.get("id") == eid:
                entry["completed"] = not entry.get("completed", False)
                done = entry["completed"]
                values = self._tree.item(eid, "values")
                new_done = "✔ Done" if done else "—"
                updated = list(values)
                updated[-1] = new_done
                self._tree.item(eid, values=updated, tags=("done",) if done else ())
                break

    def _mark_all_done(self) -> None:
        for entry in self._workout_entries:
            entry["completed"] = True
            eid = entry.get("id")
            if eid and self._tree.exists(eid):
                values = list(self._tree.item(eid, "values"))
                values[-1] = "✔ Done"
                self._tree.item(eid, values=values, tags=("done",))

    def _add_to_plan(self) -> None:
        if not self._workout_entries:
            messagebox.showinfo("No Workout", "Generate a quick workout first.")
            return
        import datetime
        today_name = datetime.datetime.now().strftime("%A")
        if today_name not in config.DAYS_OF_WEEK:
            today_name = "Monday"

        for e in self._workout_entries:
            entry = plan_module.make_plan_entry(
                exercise_id=e["id"],
                exercise_name=e["name"],
                sets=e.get("sets", 0),
                reps=e.get("reps", 0),
                duration=e.get("duration", 0),
                notes=e.get("notes", ""),
            )
            entry["completed"] = e.get("completed", False)
            plan_module.add_entry_to_day(self.app.data, today_name, entry)

        self.app.save()
        messagebox.showinfo(
            "Added to Plan",
            f"Added {len(self._workout_entries)} exercise(s) to {today_name}'s plan.",
        )


# ===========================================================================
# PROGRESS
# ===========================================================================

class ProgressPage(BasePage):

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, app)
        self._build()

    def _build(self) -> None:
        self._page_title("📊 Progress Tracker")

        # Overall stats
        overall_card = _card(self, padx=20, pady=14)
        overall_card.pack(fill="x", padx=20, pady=6)
        tk.Label(overall_card, text="Overall Progress", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w")

        bar_row = tk.Frame(overall_card, bg=CLR_CARD)
        bar_row.pack(fill="x", pady=6)
        self._progress_bar = ttk.Progressbar(bar_row, length=300, mode="determinate", maximum=100)
        self._progress_bar.pack(side="left", padx=(0, 12))
        self._pct_lbl = tk.Label(bar_row, text="0%", bg=CLR_CARD, fg=CLR_ACCENT, font=FONT_HEADING)
        self._pct_lbl.pack(side="left")

        self._overall_lbl = tk.Label(overall_card, text="", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_BODY, justify="left")
        self._overall_lbl.pack(anchor="w")

        # Weekly breakdown
        weekly_card = _card(self, padx=20, pady=14)
        weekly_card.pack(fill="both", expand=True, padx=20, pady=6)
        tk.Label(weekly_card, text="Daily Breakdown", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w", pady=(0, 6))

        cols = ("Day", "Planned", "Completed", "Remaining", "Progress%", "Duration")
        self._tree = ttk.Treeview(weekly_card, columns=cols, show="headings", height=8)
        widths = {"Day": 110, "Planned": 80, "Completed": 90, "Remaining": 90, "Progress%": 90, "Duration": 130}
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=widths.get(col, 90), anchor="center")
        self._tree.column("Day", anchor="w")
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("done", foreground=CLR_SUCCESS)
        self._tree.tag_configure("partial", foreground=CLR_WARNING)
        self._tree.tag_configure("none", foreground=CLR_MUTED)

        # Action buttons
        btn_row = tk.Frame(self, bg=CLR_BG, padx=20, pady=8)
        btn_row.pack(fill="x")
        _btn(btn_row, "🔄 Refresh", self.on_show).pack(side="left", padx=4)
        _btn(btn_row, "🔄 Reset All Completions", self._reset, color=CLR_WARNING).pack(side="left", padx=4)

    def on_show(self) -> None:
        p = prog_module.calculate_overall_progress(self.app.data)
        self._progress_bar["value"] = p["percentage"]
        self._pct_lbl.configure(text=f"{p['percentage']:.1f}%")
        self._overall_lbl.configure(text=(
            f"Total planned:    {p['total']}\n"
            f"Completed:        {p['completed']}\n"
            f"Remaining:        {p['remaining']}\n"
            f"Total duration:   {prog_module.format_duration(p['total_duration_min'])}\n"
            f"Done duration:    {prog_module.format_duration(p['completed_duration_min'])}"
        ))

        breakdown = prog_module.calculate_weekly_breakdown(self.app.data)
        self._tree.delete(*self._tree.get_children())
        for d in breakdown:
            tag = "none"
            if d["total"] > 0:
                tag = "done" if d["completed"] == d["total"] else "partial"
            dur_str = prog_module.format_duration(d["total_duration_min"])
            self._tree.insert("", "end", values=(
                d["day"], d["total"], d["completed"], d["remaining"],
                f"{d['percentage']:.1f}%", dur_str,
            ), tags=(tag,))

    def _reset(self) -> None:
        if not messagebox.askyesno("Reset", "Mark all exercises across the week as not completed?"):
            return
        plan_module.reset_all_completions(self.app.data)
        self.app.save()
        self.on_show()


# ===========================================================================
# SETTINGS
# ===========================================================================

class SettingsPage(BasePage):

    def __init__(self, parent: tk.Widget, app: App) -> None:
        super().__init__(parent, app)
        self._build()

    def _build(self) -> None:
        self._page_title("⚙️ Settings")

        # --- IBM Granite config info ---
        granite_card = _card(self, padx=20, pady=16)
        granite_card.pack(fill="x", padx=20, pady=8)

        tk.Label(granite_card, text="IBM Granite Configuration", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w")
        tk.Label(granite_card, text="Current status (read from environment / .env file):", bg=CLR_CARD, fg=CLR_MUTED, font=FONT_SMALL).pack(anchor="w", pady=(4, 0))

        self._granite_status_lbl = tk.Label(
            granite_card, text="", bg=CLR_CARD, fg=CLR_TEXT,
            font=FONT_MONO, justify="left",
        )
        self._granite_status_lbl.pack(anchor="w", pady=4)

        tk.Label(
            granite_card,
            text=(
                "To configure IBM Granite:\n"
                "1. Create a .env file in the application folder.\n"
                "2. Set IBM_GRANITE_API_KEY, IBM_WATSONX_PROJECT_ID, and optionally IBM_GRANITE_ENDPOINT & IBM_GRANITE_MODEL.\n"
                "3. Restart the application.\n\n"
                "See README.md for full setup instructions."
            ),
            bg=CLR_CARD, fg=CLR_TEXT, font=FONT_BODY, justify="left",
        ).pack(anchor="w", padx=4)

        # --- Data management ---
        data_card = _card(self, padx=20, pady=16)
        data_card.pack(fill="x", padx=20, pady=8)
        tk.Label(data_card, text="Data Management", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w")

        btn_row = tk.Frame(data_card, bg=CLR_CARD)
        btn_row.pack(fill="x", pady=6)
        _btn(btn_row, "💾 Save Data Now", lambda: (self.app.save(), messagebox.showinfo("Saved", "Data saved successfully."))).pack(side="left", padx=4)
        _btn(btn_row, "⚠️ Clear ALL Data", self._clear_all, color=CLR_DANGER).pack(side="left", padx=8)

        self._data_path_lbl = tk.Label(
            data_card, text=f"Data file: {config.DATA_FILE}",
            bg=CLR_CARD, fg=CLR_MUTED, font=FONT_SMALL,
        )
        self._data_path_lbl.pack(anchor="w", pady=2)

        # --- App info ---
        info_card = _card(self, padx=20, pady=16)
        info_card.pack(fill="x", padx=20, pady=8)
        tk.Label(info_card, text="About", bg=CLR_CARD, fg=CLR_TEXT, font=FONT_HEADING).pack(anchor="w")
        tk.Label(
            info_card,
            text=(
                f"{config.APP_TITLE}  v{config.APP_VERSION}\n"
                "Built with Python 3 + Tkinter\n"
                "AI powered by IBM Granite via watsonx.ai"
            ),
            bg=CLR_CARD, fg=CLR_TEXT, font=FONT_BODY, justify="left",
        ).pack(anchor="w")

    def on_show(self) -> None:
        api_key_status = "✔ Set" if config.IBM_GRANITE_API_KEY else "✗ Not set"
        project_status = "✔ Set" if config.IBM_WATSONX_PROJECT_ID else "✗ Not set"
        self._granite_status_lbl.configure(text=(
            f"  IBM_GRANITE_API_KEY       : {api_key_status}\n"
            f"  IBM_WATSONX_PROJECT_ID    : {project_status}\n"
            f"  IBM_GRANITE_ENDPOINT      : {config.IBM_GRANITE_ENDPOINT}\n"
            f"  IBM_GRANITE_MODEL         : {config.IBM_GRANITE_MODEL}\n"
            f"  GRANITE_MAX_NEW_TOKENS    : {config.GRANITE_MAX_NEW_TOKENS}\n"
            f"  Ready for AI features     : {'Yes ✔' if config.granite_is_configured() else 'No ✗ – credentials required'}"
        ))

    def _clear_all(self) -> None:
        if not messagebox.askyesno(
            "Clear All Data",
            "This will permanently delete ALL exercises, plans, and AI-saved plans.\n\nAre you sure?",
        ):
            return
        import storage as _s
        self.app.data = _s._deep_merge(_s._DEFAULT_DATA, {})
        self.app.save()
        messagebox.showinfo("Cleared", "All data has been cleared.")
