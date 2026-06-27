import customtkinter as ctk
from tkinter import filedialog, messagebox
import csv
import hashlib
import json
import os
import random
import shutil
import string
import threading
import time
import urllib.request
from datetime import datetime
import database

THEME_SETTING_KEY = "theme"
DEFAULT_THEME = "dark"
THEME_OPTIONS = ["Dark", "Light", "System"]
THEME_VALUES = {"dark", "light", "system"}

AUTO_LOCK_ENABLED_SETTING_KEY = "auto_lock_enabled"
AUTO_LOCK_TIMEOUT_SETTING_KEY = "auto_lock_timeout_seconds"
AUTO_LOCK_TIMEOUT_OPTIONS = {
    "1 minute": 60,
    "5 minutes": 300,
    "10 minutes": 600,
    "30 minutes": 1800,
}
DEFAULT_AUTO_LOCK_TIMEOUT_SECONDS = AUTO_LOCK_TIMEOUT_OPTIONS["5 minutes"]
AUTO_LOCK_CHECK_INTERVAL_MS = 1000
VAULT_VIEW_MODE_SETTING_KEY = "vault_view_mode"
DEFAULT_VAULT_VIEW_MODE = "tiles"
VAULT_VIEW_MODE_VALUES = {"tiles", "list"}
VAULT_VIEW_MODE_LABELS = {
    "tiles": "Tiles",
    "list": "List",
}

APP_BG = ("#f1f5f9", "#0f172a")
SIDEBAR_BG = ("#ffffff", "#020617")
CARD_BG = ("#ffffff", "#111827")
CARD_SOFT = ("#e2e8f0", "#1f2937")
CARD_SOFT_HOVER = ("#cbd5e1", "#334155")
NEUTRAL_BUTTON_BG = ("#f8fafc", "#334155")
NEUTRAL_BUTTON_HOVER = ("#e2e8f0", "#475569")
INPUT_BG = ("#f8fafc", "#0b1220")
FAVORITE_BUTTON_BG = ("#facc15", "#ca8a04")
FAVORITE_BUTTON_HOVER = ("#eab308", "#a16207")
FAVORITE_BUTTON_TEXT = "#111827"

TEXT_PRIMARY = ("#0f172a", "#f8fafc")
TEXT_SECONDARY = ("#334155", "#94a3b8")
TEXT_MUTED = ("#64748b", "#64748b")
TEXT_ON_ACCENT = "#ffffff"

ACCENT = "#7c3aed"
ACCENT_HOVER = "#6d28d9"
HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/{prefix}"
PASSWORD_UPDATE_THRESHOLD_DAYS = 180

AUDIT_SUCCESS = "#10b981"
AUDIT_INFO = "#38bdf8"
AUDIT_GOOD = "#22c55e"
AUDIT_WARNING = "#f59e0b"
AUDIT_DANGER = "#ef4444"
AUDIT_PANEL = ("#f8fafc", "#0b1220")
AUDIT_PANEL_SOFT = ("#eef2ff", "#172033")
AUDIT_BORDER = ("#dbeafe", "#1e3a5f")

SECURITY_RATINGS = [
    (95, "Excellent", AUDIT_SUCCESS),
    (85, "Very Good", AUDIT_INFO),
    (70, "Good", AUDIT_GOOD),
    (50, "Needs Improvement", AUDIT_WARNING),
    (0, "Critical", AUDIT_DANGER),
]

SECURITY_SCORE_ANIMATION_STEPS = [0, 18, 37, 64, 82, 92]
SECURITY_SCORE_ANIMATION_MS = 1000

PASSWORD_HEALTH_STYLES = {
    "Strong": {
        "bg": ("#dcfce7", "#052e16"),
        "text": ("#166534", "#86efac"),
        "reason": "Good password strength",
    },
    "Medium": {
        "bg": ("#ffedd5", "#431407"),
        "text": ("#c2410c", "#fdba74"),
        "reason": "Could be stronger",
    },
    "Weak": {
        "bg": ("#fee2e2", "#450a0a"),
        "text": ("#b91c1c", "#fca5a5"),
    },
}

EXPOSURE_STATUS_STYLES = {
    "not_checked": {
        "label": "⚪ Not checked",
        "detail": "",
        "bg": ("#e2e8f0", "#334155"),
        "text": ("#475569", "#cbd5e1"),
    },
    "checking": {
        "label": "⚪ Checking...",
        "detail": "",
        "bg": ("#e2e8f0", "#334155"),
        "text": ("#475569", "#cbd5e1"),
    },
    "safe": {
        "label": "🟢 Safe",
        "detail": "No known exposure found",
        "bg": ("#dcfce7", "#052e16"),
        "text": ("#166534", "#86efac"),
    },
    "exposed": {
        "label": "🔴 Exposed",
        "detail": "Found in {count} known breaches",
        "bg": ("#fee2e2", "#450a0a"),
        "text": ("#b91c1c", "#fca5a5"),
    },
    "failed": {
        "label": "⚪ Failed",
        "detail": "Exposure check failed",
        "bg": ("#e2e8f0", "#334155"),
        "text": ("#475569", "#cbd5e1"),
    },
}

DANGER_HOVER = ("#fee2e2", "#991b1b")
DANGER_TEXT = ("#b91c1c", "#fca5a5")
BORDER = ("#cbd5e1", "#334155")


def normalize_theme(theme):
    normalized = str(theme or DEFAULT_THEME).strip().lower()
    if normalized not in THEME_VALUES:
        return DEFAULT_THEME
    return normalized


def get_theme_label(theme):
    return normalize_theme(theme).title()


def normalize_vault_view_mode(view_mode):
    normalized = str(view_mode or DEFAULT_VAULT_VIEW_MODE).strip().lower()

    if normalized == "tile":
        normalized = "tiles"

    if normalized not in VAULT_VIEW_MODE_VALUES:
        return DEFAULT_VAULT_VIEW_MODE

    return normalized


def get_vault_view_mode_label(view_mode):
    return VAULT_VIEW_MODE_LABELS[normalize_vault_view_mode(view_mode)]


def parse_updated_at(updated_at):
    updated_at_text = str(updated_at or "").strip()

    if not updated_at_text:
        return None

    try:
        return datetime.strptime(updated_at_text, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


def get_password_age_days(updated_at):
    changed_at = parse_updated_at(updated_at)

    if changed_at is None:
        return None

    return max((datetime.now().date() - changed_at.date()).days, 0)


def format_password_age_value(age_days):
    if age_days is None:
        return "Unknown"

    if age_days == 0:
        return "Today"

    day_label = "day" if age_days == 1 else "days"
    return f"{age_days} {day_label}"


def get_password_age_color(age_days):
    if age_days is None:
        return TEXT_MUTED

    if age_days <= 30:
        return ("#15803d", "#86efac")

    if age_days <= 179:
        return ("#ca8a04", "#fde047")

    return DANGER_TEXT


def load_saved_theme():
    database.create_table()
    theme = normalize_theme(database.get_setting(THEME_SETTING_KEY, DEFAULT_THEME))
    ctk.set_appearance_mode(theme)
    return theme


def load_saved_vault_view_mode():
    return normalize_vault_view_mode(
        database.get_setting(
            VAULT_VIEW_MODE_SETTING_KEY,
            DEFAULT_VAULT_VIEW_MODE
        )
    )


def setting_to_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def normalize_auto_lock_timeout(value):
    if value in AUTO_LOCK_TIMEOUT_OPTIONS:
        return AUTO_LOCK_TIMEOUT_OPTIONS[value]

    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return DEFAULT_AUTO_LOCK_TIMEOUT_SECONDS

    if seconds in AUTO_LOCK_TIMEOUT_OPTIONS.values():
        return seconds

    return DEFAULT_AUTO_LOCK_TIMEOUT_SECONDS


def get_auto_lock_timeout_label(seconds):
    normalized_seconds = normalize_auto_lock_timeout(seconds)

    for label, value in AUTO_LOCK_TIMEOUT_OPTIONS.items():
        if value == normalized_seconds:
            return label

    return "5 minutes"


def load_saved_auto_lock_settings():
    enabled = setting_to_bool(database.get_setting(AUTO_LOCK_ENABLED_SETTING_KEY, "0"))
    timeout_seconds = normalize_auto_lock_timeout(
        database.get_setting(
            AUTO_LOCK_TIMEOUT_SETTING_KEY,
            DEFAULT_AUTO_LOCK_TIMEOUT_SECONDS
        )
    )

    return enabled, timeout_seconds


class SecurePassApp(ctk.CTk):
    def __init__(self):
        initial_theme = load_saved_theme()
        auto_lock_enabled, auto_lock_timeout_seconds = load_saved_auto_lock_settings()
        vault_view_mode = load_saved_vault_view_mode()
        super().__init__()

        self.current_theme = initial_theme
        self.auto_lock_enabled = auto_lock_enabled
        self.auto_lock_timeout_seconds = auto_lock_timeout_seconds
        self.vault_view_mode = vault_view_mode
        self.auto_lock_after_id = None
        self.last_activity_time = time.monotonic()
        self.editing_password_id = None
        self.exposure_statuses = {}
        self.exposure_checks_in_flight = set()
        self.exposure_pending_widgets = {}
        self.dashboard_audit_data = None
        self.security_score_after_ids = []
        self.security_score_current = 0
        self.toast = None
        self.toast_after_id = None

        self.title("SecurePass Manager")
        self.geometry("1120x700")
        self.minsize(1000, 620)
        self.configure(fg_color=APP_BG)
        self.crypto = None
        self.bind_activity_events()
        self.schedule_auto_lock_check()

        if database.has_master_password():
            self.create_unlock_screen()
        else:
            self.create_master_setup_screen()

    def clear_window(self):
        if self.toast_after_id is not None:
            self.after_cancel(self.toast_after_id)
            self.toast_after_id = None

        self.cancel_security_score_animation()

        for widget in self.winfo_children():
            widget.destroy()
        self.toast = None

    def show_toast(self, message, kind="success"):
        colors = {
            "success": {
                "bg": "#14532d",
                "border": "#22c55e",
                "text": "#dcfce7",
            },
            "error": {
                "bg": "#7f1d1d",
                "border": "#ef4444",
                "text": "#fee2e2",
            }
        }
        style = colors.get(kind, colors["success"])

        if self.toast_after_id is not None:
            self.after_cancel(self.toast_after_id)
            self.toast_after_id = None

        if self.toast is not None and self.toast.winfo_exists():
            self.toast.destroy()

        self.toast = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=style["bg"],
            border_width=1,
            border_color=style["border"]
        )

        ctk.CTkLabel(
            self.toast,
            text=message,
            text_color=style["text"],
            font=("Segoe UI", 13, "bold")
        ).pack(padx=18, pady=12)

        self.toast.place(relx=1, rely=1, anchor="se", x=-24, y=-24)
        self.toast.lift()
        self.toast_after_id = self.after(2000, self.hide_toast)

    def hide_toast(self):
        if self.toast is not None and self.toast.winfo_exists():
            self.toast.destroy()

        self.toast = None
        self.toast_after_id = None

    def bind_activity_events(self):
        self.bind_all("<Key>", self.record_activity, add="+")
        self.bind_all("<Motion>", self.record_activity, add="+")
        self.bind_all("<Button>", self.record_activity, add="+")

    def record_activity(self, event=None):
        self.last_activity_time = time.monotonic()

    def schedule_auto_lock_check(self):
        if self.auto_lock_after_id is None:
            self.auto_lock_after_id = self.after(
                AUTO_LOCK_CHECK_INTERVAL_MS,
                self.check_auto_lock
            )

    def check_auto_lock(self):
        self.auto_lock_after_id = None

        if self.crypto is not None and self.auto_lock_enabled:
            idle_seconds = time.monotonic() - self.last_activity_time

            if idle_seconds >= self.auto_lock_timeout_seconds:
                self.auto_lock_vault()

        self.schedule_auto_lock_check()

    def auto_lock_vault(self):
        if self.crypto is None:
            return

        self.clear_sensitive_fields()
        self.close_change_password_modal()
        self.close_security_recommendations_modal()

        self.editing_password_id = None
        self.crypto = None
        self.create_unlock_screen()
        self.show_toast("Vault locked due to inactivity.")

    def close_change_password_modal(self):
        modal = getattr(self, "change_password_modal", None)

        try:
            if modal is not None and modal.winfo_exists():
                modal.grab_release()
                modal.destroy()
        except Exception:
            pass

    def close_security_recommendations_modal(self):
        modal = getattr(self, "security_recommendations_modal", None)

        try:
            if modal is not None and modal.winfo_exists():
                modal.grab_release()
                modal.destroy()
        except Exception:
            pass

    def clear_sensitive_fields(self):
        for entry_name in [
            "master_password_entry",
            "confirm_master_entry",
            "unlock_password_entry",
            "password_entry",
            "generated_password_entry",
        ]:
            entry = getattr(self, entry_name, None)

            try:
                if entry is not None and entry.winfo_exists():
                    entry.delete(0, "end")
            except Exception:
                pass

    def create_master_setup_screen(self):
        self.clear_window()
        self.configure(fg_color=APP_BG)

        container = ctk.CTkFrame(self, width=430, height=360, corner_radius=24, fg_color=CARD_BG)
        container.pack(expand=True)
        container.pack_propagate(False)

        ctk.CTkLabel(container, text="SecurePass", font=("Segoe UI", 32, "bold"), text_color=TEXT_PRIMARY).pack(pady=(45, 6))
        ctk.CTkLabel(container, text="Create your master password", font=("Segoe UI", 14), text_color=TEXT_SECONDARY).pack(pady=(0, 28))

        self.master_password_entry = self.create_input(container, "Master Password", show="•", width=310)
        self.master_password_entry.pack(pady=8)

        self.confirm_master_entry = self.create_input(container, "Confirm Master Password", show="•", width=310)
        self.confirm_master_entry.pack(pady=8)
        self.confirm_master_entry.bind("<Return>", lambda event: self.save_master_password())

        ctk.CTkButton(
            container,
            text="Create Vault",
            width=310,
            height=46,
            corner_radius=14,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 14, "bold"),
            command=self.save_master_password
        ).pack(pady=(28, 45))

    def save_master_password(self):
        password = self.master_password_entry.get().strip()
        confirm = self.confirm_master_entry.get().strip()

        if not password or not confirm:
            messagebox.showerror("Error", "Please fill both fields.")
            return

        if len(password) < 6:
            messagebox.showerror("Weak Password", "Master password must be at least 6 characters.")
            return

        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        database.set_master_password(password)
        self.crypto = database.create_crypto(password)
        self.create_app_layout()

    def create_unlock_screen(self):
        self.clear_window()
        self.configure(fg_color=APP_BG)

        container = ctk.CTkFrame(
            self,
            width=430,
            height=380,
            corner_radius=24,
            fg_color=CARD_BG
        )
        container.pack(expand=True)
        container.pack_propagate(False)

        ctk.CTkLabel(
            container,
            text="🔒 SecurePass",
            font=("Segoe UI", 34, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(42, 8))

        ctk.CTkLabel(
            container,
            text="Your vault is encrypted.",
            font=("Segoe UI", 15, "bold"),
            text_color=TEXT_SECONDARY
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            container,
            text="Enter your master password to continue.",
            font=("Segoe UI", 13),
            text_color=TEXT_MUTED
        ).pack(pady=(0, 26))

        unlock_wrapper, self.unlock_password_entry = self.create_password_input_with_toggle(
            container,
            "Master Password",
            width=310
        )
        unlock_wrapper.pack(pady=8)

        self.unlock_password_entry.bind(
            "<Return>",
            lambda event: self.unlock_vault()
        )

        ctk.CTkButton(
            container,
            text="🔓 Unlock Vault",
            width=310,
            height=46,
            corner_radius=14,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 14, "bold"),
            command=self.unlock_vault
        ).pack(pady=(22, 16))

        ctk.CTkLabel(
            container,
            text="Forgot your master password? Your data cannot be recovered.",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED
        ).pack(pady=(4, 0))

    def unlock_vault(self):
        password = self.unlock_password_entry.get().strip()

        if database.verify_master_password(password):
            self.crypto = database.create_crypto(password)
            self.create_app_layout()
        else:
            messagebox.showerror("Access Denied", "Incorrect master password.")

    def create_app_layout(self):
        self.last_activity_time = time.monotonic()
        self.schedule_auto_lock_check()
        self.clear_window()
        self.configure(fg_color=APP_BG)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=SIDEBAR_BG)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="SecurePass", font=("Segoe UI", 27, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=26, pady=(32, 4))
        ctk.CTkLabel(self.sidebar, text="Password Manager", font=("Segoe UI", 13), text_color=TEXT_MUTED).pack(anchor="w", padx=26, pady=(0, 34))

        self.dashboard_button = self.create_sidebar_button("Dashboard", self.show_dashboard)
        self.dashboard_button.pack(fill="x", padx=18, pady=6)

        self.vault_button = self.create_sidebar_button("Vault", self.show_vault)
        self.vault_button.pack(fill="x", padx=18, pady=6)

        self.generator_button = self.create_sidebar_button("Generator", self.show_generator)
        self.generator_button.pack(fill="x", padx=18, pady=6)

        self.settings_button = self.create_sidebar_button("⚙ Settings", self.show_settings)
        self.settings_button.pack(fill="x", padx=18, pady=6)

        self.clear_button = self.create_sidebar_button("Clear Form", self.clear_form)
        self.clear_button.pack(fill="x", padx=18, pady=6)

        ctk.CTkLabel(self.sidebar, text="SQLite • Encrypted Vault", text_color=TEXT_MUTED, font=("Segoe UI", 12)).pack(side="bottom", pady=26)

        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=APP_BG)
        self.main_area.pack(side="right", fill="both", expand=True)

        self.header_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=34, pady=(28, 10))

        self.page_title = ctk.CTkLabel(self.header_frame, text="Dashboard", font=("Segoe UI", 32, "bold"), text_color=TEXT_PRIMARY)
        self.page_title.pack(side="left")

        self.search_entry = self.create_input(self.header_frame, "Search website, username or note...", width=330)
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_passwords())

        self.create_dashboard_view()
        self.create_vault_view()
        self.create_generator_view()
        self.create_settings_view()

        self.show_dashboard()

    def create_sidebar_button(self, text, command):
        return ctk.CTkButton(
            self.sidebar,
            text=text,
            height=46,
            corner_radius=14,
            anchor="w",
            font=("Segoe UI", 14, "bold"),
            fg_color="transparent",
            hover_color=CARD_SOFT,
            text_color=TEXT_SECONDARY,
            command=command
        )

    def set_active_nav(self, active):
        buttons = {
            "dashboard": self.dashboard_button,
            "vault": self.vault_button,
            "generator": self.generator_button,
            "settings": self.settings_button,
        }

        for name, button in buttons.items():
            button.configure(
                fg_color=ACCENT if active == name else "transparent",
                hover_color=ACCENT_HOVER if active == name else CARD_SOFT,
                text_color=TEXT_ON_ACCENT if active == name else TEXT_SECONDARY
            )

    def create_input(self, parent, placeholder, show=None, width=240):
        return ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            show=show,
            width=width,
            height=44,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
            fg_color=INPUT_BG,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            font=("Segoe UI", 13)
        )

    def create_primary_button(self, parent, text, command):
        return ctk.CTkButton(
            parent,
            text=text,
            height=46,
            corner_radius=14,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 14, "bold"),
            command=command
        )

    def create_dashboard_view(self):
        self.dashboard_view = ctk.CTkScrollableFrame(
            self.main_area,
            fg_color="transparent",
            scrollbar_button_color=CARD_SOFT,
            scrollbar_button_hover_color=CARD_SOFT_HOVER
        )

        audit_shadow = ctk.CTkFrame(
            self.dashboard_view,
            corner_radius=30,
            fg_color=("#d8e2ef", "#050816")
        )
        audit_shadow.pack(fill="x", pady=(0, 24))

        self.security_audit_card = ctk.CTkFrame(
            audit_shadow,
            corner_radius=28,
            fg_color=CARD_BG,
            border_width=1,
            border_color=AUDIT_BORDER
        )
        self.security_audit_card.pack(fill="x", pady=(0, 6))
        self.create_security_audit_card(self.security_audit_card)

        bottom = ctk.CTkFrame(self.dashboard_view, corner_radius=24, fg_color=CARD_BG)
        bottom.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(
            bottom,
            text="Vault Overview",
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=26, pady=(24, 6))

        ctk.CTkLabel(
            bottom,
            text="A quick summary of your saved passwords and security health.",
            font=("Segoe UI", 13),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=26, pady=(0, 24))

        self.dashboard_summary_frame = ctk.CTkFrame(
            bottom,
            fg_color="transparent"
        )
        self.dashboard_summary_frame.pack(fill="x", padx=26, pady=(0, 24))

    def create_security_audit_card(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 10))

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_block,
            text="🛡 Security Score",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 25, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_block,
            text="Offline vault audit",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(4, 0))

        self.security_rating_pill = ctk.CTkLabel(
            header,
            text="Excellent",
            width=138,
            height=36,
            corner_radius=18,
            fg_color=AUDIT_SUCCESS,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 13, "bold")
        )
        self.security_rating_pill.pack(side="right", padx=(18, 0))

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="x", padx=28, pady=(4, 18))
        body.grid_columnconfigure(0, weight=2, uniform="audit_body")
        body.grid_columnconfigure(1, weight=3, uniform="audit_body")

        score_panel = ctk.CTkFrame(
            body,
            corner_radius=24,
            fg_color=AUDIT_PANEL,
            border_width=1,
            border_color=BORDER
        )
        score_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.security_score_label = ctk.CTkLabel(
            score_panel,
            text="0 / 100",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 58, "bold")
        )
        self.security_score_label.pack(anchor="w", padx=24, pady=(24, 0))

        self.security_score_subtitle = ctk.CTkLabel(
            score_panel,
            text="Excellent Security",
            text_color=AUDIT_SUCCESS,
            font=("Segoe UI", 20, "bold")
        )
        self.security_score_subtitle.pack(anchor="w", padx=26, pady=(0, 18))

        self.security_score_progress = ctk.CTkProgressBar(
            score_panel,
            height=14,
            corner_radius=10,
            fg_color=CARD_SOFT,
            progress_color=AUDIT_SUCCESS
        )
        self.security_score_progress.pack(fill="x", padx=26, pady=(0, 16))
        self.security_score_progress.set(0)

        ctk.CTkLabel(
            score_panel,
            text="Your vault follows modern security best practices.",
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 13),
            wraplength=290,
            justify="left"
        ).pack(anchor="w", padx=26, pady=(0, 24))

        stats_panel = ctk.CTkFrame(
            body,
            corner_radius=24,
            fg_color=AUDIT_PANEL,
            border_width=1,
            border_color=BORDER
        )
        stats_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        ctk.CTkLabel(
            stats_panel,
            text="Quick Statistics",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=22, pady=(20, 14))

        self.audit_stats_grid = ctk.CTkFrame(stats_panel, fg_color="transparent")
        self.audit_stats_grid.pack(fill="x", padx=16, pady=(0, 18))
        for column in range(3):
            self.audit_stats_grid.grid_columnconfigure(column, weight=1, uniform="audit_stats")

        checklist_panel = ctk.CTkFrame(
            parent,
            corner_radius=24,
            fg_color=AUDIT_PANEL,
            border_width=1,
            border_color=BORDER
        )
        checklist_panel.pack(fill="x", padx=28, pady=(0, 18))

        ctk.CTkLabel(
            checklist_panel,
            text="Security Checklist",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=22, pady=(20, 12))

        self.security_checklist_frame = ctk.CTkFrame(
            checklist_panel,
            fg_color="transparent"
        )
        self.security_checklist_frame.pack(fill="x", padx=18, pady=(0, 18))

        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        action_row.pack(fill="x", padx=28, pady=(0, 26))

        self.security_score_hint = ctk.CTkLabel(
            action_row,
            text="Recommendations are generated locally from your vault data.",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 12)
        )
        self.security_score_hint.pack(side="left")

        ctk.CTkButton(
            action_row,
            text="Improve My Score →",
            width=190,
            height=46,
            corner_radius=16,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 14, "bold"),
            command=self.open_security_recommendations_modal
        ).pack(side="right")

    def create_stat_card(self, parent, title, value, accent_color):
        card = ctk.CTkFrame(parent, height=130, corner_radius=24, fg_color=CARD_BG)
        card.pack_propagate(False)

        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", padx=22, pady=(22, 4))

        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=("Segoe UI", 34, "bold"),
            text_color=TEXT_PRIMARY
        )
        value_label.pack(anchor="w", padx=22)

        ctk.CTkFrame(card, height=4, fg_color=accent_color, corner_radius=20).pack(fill="x", padx=22, pady=(16, 0))

        card.value_label = value_label
        return card

    def update_dashboard(self, animate=False):
        rows = database.get_passwords("", self.crypto)
        favorites = database.get_favorites(self.crypto)
        audit = self.build_security_audit(rows, favorites)
        self.dashboard_audit_data = audit

        total = audit["total"]
        strong = audit["strong"]
        medium = audit["medium"]
        weak = audit["weak"]
        reused = audit["reused"]
        passwords_needing_update = audit["expired_entries"]
        reused_groups = audit["reused_groups"]

        self.refresh_security_audit_card(audit, animate=animate)

        for widget in self.dashboard_summary_frame.winfo_children():
            widget.destroy()

        if total == 0:
            ctk.CTkLabel(
                self.dashboard_summary_frame,
                text="No passwords saved yet. Add your first password from the Vault page.",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 15)
            ).pack(anchor="w", pady=10)
            self.create_password_strength_section(strong, medium, weak, total)
            self.create_expiring_passwords_section(passwords_needing_update)
            self.create_favorites_section(favorites)
            self.create_reused_password_section(reused_groups)
            return

        security_text = "Your vault looks healthy."
        security_color = "#22c55e"

        if weak > 0 or reused > 0 or passwords_needing_update:
            security_text = "Some passwords need attention."
            security_color = "#f59e0b"

        if weak >= 3 or reused >= 3 or len(passwords_needing_update) >= 3:
            security_text = "Your vault has multiple security warnings."
            security_color = "#ef4444"

        ctk.CTkLabel(
            self.dashboard_summary_frame,
            text=security_text,
            text_color=security_color,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(
            self.dashboard_summary_frame,
            text=f"{strong} strong passwords, {medium} medium passwords, {weak} weak passwords, {reused} reused password entries.",
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 14)
        ).pack(anchor="w")

        self.create_password_strength_section(strong, medium, weak, total)
        self.create_expiring_passwords_section(passwords_needing_update)
        self.create_favorites_section(favorites)
        self.create_reused_password_section(reused_groups)

    def get_security_rating(self, score):
        for minimum, label, color in SECURITY_RATINGS:
            if score >= minimum:
                return {
                    "label": label,
                    "subtitle": f"{label} Security",
                    "color": color,
                }

        label, color = "Critical", AUDIT_DANGER
        return {
            "label": label,
            "subtitle": f"{label} Security",
            "color": color,
        }

    def get_cached_exposure_status(self, password):
        if password in {"[locked]", "[decryption failed]"}:
            return self.get_exposure_failed_status()

        password_hash = self.get_password_sha1_hash(password)
        return self.exposure_statuses.get(
            password_hash,
            {
                "state": "not_checked",
                "count": 0,
                "password_hash": password_hash,
            }
        )

    def build_security_audit(self, rows, favorites):
        total = len(rows)
        favorite_count = len(favorites)
        strong = 0
        medium = 0
        weak = 0
        valid_lengths = []
        accounts_by_password = {}
        weak_entries = []
        medium_entries = []
        exposed_entries = []
        expired_entries = []
        expired_recommendation_entries = []

        for row in rows:
            password_id, website, username, password, _, updated_at, _ = row
            age_days = get_password_age_days(updated_at)

            if age_days is not None and age_days > PASSWORD_UPDATE_THRESHOLD_DAYS:
                expired_entries.append((website, username, age_days))
                expired_recommendation_entries.append({
                    "id": password_id,
                    "website": website,
                    "username": username,
                    "age_days": age_days,
                })

            if password in {"[decryption failed]", "[locked]"}:
                continue

            valid_lengths.append(len(password))
            accounts_by_password.setdefault(password, []).append({
                "id": password_id,
                "website": website,
                "username": username,
            })

            score = self.calculate_strength(password)
            _, _, _, health_reason = self.get_password_health(password)

            if score >= 4:
                strong += 1
            elif score == 3:
                medium += 1
                medium_entries.append({
                    "id": password_id,
                    "website": website,
                    "username": username,
                    "reason": health_reason,
                })
            else:
                weak += 1
                weak_entries.append({
                    "id": password_id,
                    "website": website,
                    "username": username,
                    "reason": health_reason,
                })

            exposure_status = self.get_cached_exposure_status(password)
            if exposure_status.get("state") == "exposed":
                exposed_entries.append({
                    "id": password_id,
                    "website": website,
                    "username": username,
                    "count": exposure_status.get("count", 0),
                })

        reused_account_groups = [
            accounts
            for accounts in accounts_by_password.values()
            if len(accounts) > 1
        ]
        reused_groups = [
            [
                (account["website"], account["username"])
                for account in accounts
            ]
            for accounts in reused_account_groups
        ]
        reused_entries = [
            account
            for accounts in reused_account_groups
            for account in accounts
        ]

        exposed = len(exposed_entries)
        expired = len(expired_entries)
        reused = len(reused_entries)
        average_length = (
            int(round(sum(valid_lengths) / len(valid_lengths)))
            if valid_lengths else 0
        )

        penalty = (
            (weak * 6) +
            (medium * 2) +
            (reused * 10) +
            (exposed * 12) +
            (expired * 5)
        )
        score = max(0, min(100, 100 - penalty))
        rating = self.get_security_rating(score)

        recommendations = self.build_security_recommendations(
            weak_entries,
            medium_entries,
            reused_entries,
            exposed_entries,
            expired_recommendation_entries
        )
        warnings = self.build_security_warnings(
            weak,
            reused,
            exposed,
            expired
        )

        return {
            "score": score,
            "rating": rating,
            "total": total,
            "favorites": favorite_count,
            "strong": strong,
            "medium": medium,
            "weak": weak,
            "exposed": exposed,
            "expired": expired,
            "reused": reused,
            "average_length": average_length,
            "expired_entries": expired_entries,
            "reused_groups": reused_groups,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def build_security_warnings(self, weak, reused, exposed, expired):
        warnings = []

        if weak:
            warnings.append({
                "text": f"❌ {weak} {self.pluralize(weak, 'Weak Password')}",
                "color": AUDIT_DANGER,
            })

        if reused:
            warnings.append({
                "text": f"❌ {reused} {self.pluralize(reused, 'Reused Password')}",
                "color": AUDIT_DANGER,
            })

        if exposed:
            warnings.append({
                "text": f"❌ {exposed} {self.pluralize(exposed, 'Exposed Password')}",
                "color": AUDIT_DANGER,
            })

        if expired:
            verb = "Needs" if expired == 1 else "Need"
            warnings.append({
                "text": f"⚠ {expired} {self.pluralize(expired, 'Password')} {verb} Updating",
                "color": AUDIT_WARNING,
            })

        return warnings

    def build_security_recommendations(
        self,
        weak_entries,
        medium_entries,
        reused_entries,
        exposed_entries,
        expired_entries
    ):
        recommendations = []

        for entry in exposed_entries:
            recommendations.append({
                "website": entry["website"],
                "username": entry["username"],
                "issue": "Password found in known data breaches.",
                "recommendation": "Replace this password immediately.",
                "priority": "High",
            })

        for entry in weak_entries:
            recommendations.append({
                "website": entry["website"],
                "username": entry["username"],
                "issue": "Weak password.",
                "recommendation": "Generate a password with at least 14 characters.",
                "priority": "High",
            })

        for entry in reused_entries:
            recommendations.append({
                "website": entry["website"],
                "username": entry["username"],
                "issue": "Password reused.",
                "recommendation": "Generate a unique password.",
                "priority": "High",
            })

        for entry in expired_entries:
            recommendations.append({
                "website": entry["website"],
                "username": entry["username"],
                "issue": f"Password is {entry['age_days']} days old.",
                "recommendation": "Change this password.",
                "priority": "Medium",
            })

        for entry in medium_entries:
            recommendations.append({
                "website": entry["website"],
                "username": entry["username"],
                "issue": "Medium password strength.",
                "recommendation": "Increase length and include mixed character types.",
                "priority": "Low",
            })

        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        return sorted(
            recommendations,
            key=lambda item: (
                priority_order.get(item["priority"], 3),
                item["website"].lower()
            )
        )

    def pluralize(self, count, singular):
        return singular if count == 1 else f"{singular}s"

    def refresh_security_audit_card(self, audit, animate=False):
        if not hasattr(self, "security_score_label"):
            return

        rating = audit["rating"]
        rating_color = rating["color"]
        self.security_rating_pill.configure(
            text=rating["label"],
            fg_color=rating_color
        )
        self.security_score_subtitle.configure(
            text=rating["subtitle"],
            text_color=rating_color
        )
        self.security_score_progress.configure(progress_color=rating_color)

        if animate:
            self.animate_security_score(audit["score"])
        else:
            self.set_security_score(audit["score"])

        self.refresh_audit_statistics(audit)
        self.refresh_security_checklist(audit)

        recommendation_count = len(audit["recommendations"])
        hint = (
            "Everything looks secure."
            if recommendation_count == 0
            else f"{recommendation_count} local recommendations available."
        )
        self.security_score_hint.configure(text=hint)

    def refresh_audit_statistics(self, audit):
        for widget in self.audit_stats_grid.winfo_children():
            widget.destroy()

        stats = [
            ("Passwords", audit["total"], "#60a5fa"),
            ("Favorites", audit["favorites"], "#facc15"),
            ("Strong", audit["strong"], AUDIT_SUCCESS),
            ("Medium", audit["medium"], AUDIT_WARNING),
            ("Weak", audit["weak"], AUDIT_DANGER),
            ("Exposed", audit["exposed"], AUDIT_DANGER),
            ("Expired", audit["expired"], AUDIT_WARNING),
            ("Reused", audit["reused"], "#fb7185"),
            ("Average Password Length", f"{audit['average_length']} chars", AUDIT_INFO),
        ]

        for index, (label, value, color) in enumerate(stats):
            self.create_audit_stat_tile(
                self.audit_stats_grid,
                label,
                value,
                color,
                index // 3,
                index % 3
            )

    def create_audit_stat_tile(self, parent, label, value, color, row, column):
        tile = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color=AUDIT_PANEL_SOFT
        )
        tile.grid(row=row, column=column, sticky="ew", padx=6, pady=6)

        ctk.CTkLabel(
            tile,
            text=str(value),
            text_color=color,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            tile,
            text=label,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 11, "bold"),
            wraplength=120,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(2, 12))

    def refresh_security_checklist(self, audit):
        for widget in self.security_checklist_frame.winfo_children():
            widget.destroy()

        feature_grid = ctk.CTkFrame(
            self.security_checklist_frame,
            fg_color="transparent"
        )
        feature_grid.pack(fill="x")
        for column in range(2):
            feature_grid.grid_columnconfigure(column, weight=1, uniform="audit_checks")

        feature_rows = [
            ("✔ Encryption Enabled", self.crypto is not None, "⚠ Encryption Locked"),
            ("✔ Master Password Enabled", database.has_master_password(), "⚠ Master Password Missing"),
            ("✔ Auto Lock Enabled", self.auto_lock_enabled, "⚠ Auto Lock Disabled"),
            ("✔ Backup Available", os.path.exists(database.DB_FILE), "⚠ Backup Unavailable"),
            ("✔ Password Health Enabled", True, ""),
            ("✔ Exposure Checker Enabled", True, ""),
            ("✔ Toast Notifications Enabled", True, ""),
        ]

        for index, (enabled_text, enabled, disabled_text) in enumerate(feature_rows):
            text = enabled_text if enabled else disabled_text
            color = AUDIT_SUCCESS if enabled else AUDIT_WARNING
            self.create_security_check_tile(
                feature_grid,
                text,
                color,
                index // 2,
                index % 2
            )

        warning_frame = ctk.CTkFrame(
            self.security_checklist_frame,
            fg_color="transparent"
        )
        warning_frame.pack(fill="x", pady=(12, 0))
        warning_frame.grid_columnconfigure(0, weight=1)
        warning_frame.grid_columnconfigure(1, weight=1)

        if not audit["warnings"]:
            self.create_security_check_tile(
                warning_frame,
                "✔ Everything looks secure.",
                AUDIT_SUCCESS,
                0,
                0,
                columnspan=2
            )
            return

        for index, warning in enumerate(audit["warnings"]):
            self.create_security_check_tile(
                warning_frame,
                warning["text"],
                warning["color"],
                index // 2,
                index % 2
            )

    def create_security_check_tile(
        self,
        parent,
        text,
        color,
        row,
        column,
        columnspan=1
    ):
        tile = ctk.CTkFrame(
            parent,
            corner_radius=14,
            fg_color=AUDIT_PANEL_SOFT
        )
        tile.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=6,
            pady=5
        )

        ctk.CTkLabel(
            tile,
            text=text,
            text_color=color,
            font=("Segoe UI", 13, "bold"),
            anchor="w",
            justify="left",
            wraplength=320
        ).pack(fill="x", padx=14, pady=10)

    def cancel_security_score_animation(self):
        for after_id in self.security_score_after_ids:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass

        self.security_score_after_ids = []

    def render_security_score(self, score):
        score = max(0, min(100, int(score)))
        self.security_score_current = score

        if self.widget_exists(getattr(self, "security_score_label", None)):
            self.security_score_label.configure(text=f"{score} / 100")

        if self.widget_exists(getattr(self, "security_score_progress", None)):
            self.security_score_progress.set(score / 100)

    def set_security_score(self, score):
        self.cancel_security_score_animation()
        self.render_security_score(score)

    def animate_security_score(self, target_score):
        self.cancel_security_score_animation()

        target_score = max(0, min(100, int(target_score)))
        base_score = SECURITY_SCORE_ANIMATION_STEPS[-1]
        steps = [
            round(target_score * (step / base_score))
            for step in SECURITY_SCORE_ANIMATION_STEPS
        ]
        steps[0] = 0
        steps[-1] = target_score
        delay = SECURITY_SCORE_ANIMATION_MS // max(len(steps) - 1, 1)

        for index, value in enumerate(steps):
            after_id = self.after(
                index * delay,
                lambda value=value: self.render_security_score(value)
            )
            self.security_score_after_ids.append(after_id)

    def open_security_recommendations_modal(self):
        modal = getattr(self, "security_recommendations_modal", None)

        if modal is not None and modal.winfo_exists():
            modal.focus()
            return

        audit = self.dashboard_audit_data
        if audit is None:
            rows = database.get_passwords("", self.crypto)
            favorites = database.get_favorites(self.crypto)
            audit = self.build_security_audit(rows, favorites)
            self.dashboard_audit_data = audit

        modal_width = 720
        modal_height = 620

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - modal_width) // 2
        y = self.winfo_y() + (self.winfo_height() - modal_height) // 2

        modal = ctk.CTkToplevel(self)
        modal.title("Security Recommendations")
        modal.geometry(f"{modal_width}x{modal_height}+{max(x, 0)}+{max(y, 0)}")
        modal.minsize(640, 520)
        modal.configure(fg_color=APP_BG)
        modal.transient(self)
        modal.grab_set()
        self.security_recommendations_modal = modal

        def close_modal():
            try:
                modal.grab_release()
            except Exception:
                pass
            modal.destroy()

        modal.protocol("WM_DELETE_WINDOW", close_modal)

        header = ctk.CTkFrame(modal, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(28, 14))

        ctk.CTkLabel(
            header,
            text="Security Recommendations",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 26, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Personalized fixes generated offline from your current vault.",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 13)
        ).pack(anchor="w", pady=(5, 0))

        content = ctk.CTkScrollableFrame(
            modal,
            fg_color="transparent",
            scrollbar_button_color=CARD_SOFT,
            scrollbar_button_hover_color=CARD_SOFT_HOVER
        )
        content.pack(fill="both", expand=True, padx=30, pady=(0, 18))

        recommendations = audit["recommendations"]
        if not recommendations:
            empty_state = ctk.CTkFrame(
                content,
                corner_radius=22,
                fg_color=CARD_BG,
                border_width=1,
                border_color=BORDER
            )
            empty_state.pack(fill="x", pady=(8, 0))

            ctk.CTkLabel(
                empty_state,
                text="Everything looks secure.",
                text_color=AUDIT_SUCCESS,
                font=("Segoe UI", 20, "bold")
            ).pack(anchor="w", padx=22, pady=(22, 6))

            ctk.CTkLabel(
                empty_state,
                text="No weak, reused, exposed, or expired passwords were found.",
                text_color=TEXT_SECONDARY,
                font=("Segoe UI", 13)
            ).pack(anchor="w", padx=22, pady=(0, 22))
        else:
            for recommendation in recommendations:
                self.create_security_recommendation_item(
                    content,
                    recommendation
                )

        action_row = ctk.CTkFrame(modal, fg_color="transparent")
        action_row.pack(fill="x", padx=30, pady=(0, 28))

        ctk.CTkButton(
            action_row,
            text="Close",
            width=118,
            height=42,
            corner_radius=14,
            fg_color=CARD_SOFT,
            hover_color=CARD_SOFT_HOVER,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
            command=close_modal
        ).pack(side="right")

    def create_security_recommendation_item(self, parent, recommendation):
        priority_colors = {
            "High": AUDIT_DANGER,
            "Medium": AUDIT_WARNING,
            "Low": AUDIT_INFO,
        }
        priority = recommendation["priority"]
        priority_color = priority_colors.get(priority, TEXT_SECONDARY)

        item = ctk.CTkFrame(
            parent,
            corner_radius=22,
            fg_color=CARD_BG,
            border_width=1,
            border_color=BORDER
        )
        item.pack(fill="x", pady=(8, 12))

        top = ctk.CTkFrame(item, fg_color="transparent")
        top.pack(fill="x", padx=22, pady=(20, 8))

        ctk.CTkLabel(
            top,
            text=f"❌ {recommendation['website']}",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold")
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text=f"Priority: {priority}",
            width=106,
            height=30,
            corner_radius=15,
            fg_color=priority_color,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="right")

        if recommendation.get("username"):
            ctk.CTkLabel(
                item,
                text=recommendation["username"],
                text_color=TEXT_MUTED,
                font=("Segoe UI", 12)
            ).pack(anchor="w", padx=22, pady=(0, 8))

        ctk.CTkLabel(
            item,
            text=recommendation["issue"],
            text_color=priority_color,
            font=("Segoe UI", 14, "bold"),
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=22, pady=(0, 8))

        ctk.CTkLabel(
            item,
            text=f"Recommendation: {recommendation['recommendation']}",
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 13),
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=22, pady=(0, 20))

    def create_password_strength_section(self, strong, medium, weak, total):
        ctk.CTkFrame(
            self.dashboard_summary_frame,
            height=1,
            fg_color=BORDER
        ).pack(fill="x", pady=(22, 18))

        chart_card = ctk.CTkFrame(
            self.dashboard_summary_frame,
            corner_radius=18,
            fg_color=CARD_SOFT
        )
        chart_card.pack(fill="x")

        ctk.CTkLabel(
            chart_card,
            text="Password Strength",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=18, pady=(16, 14))

        for label, count, color in [
            ("Strong", strong, "#22c55e"),
            ("Medium", medium, "#f59e0b"),
            ("Weak", weak, "#ef4444"),
        ]:
            self.create_strength_chart_row(chart_card, label, count, total, color)

    def create_strength_chart_row(self, parent, label, count, total, color):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(
            row,
            text=f"{label} {count}",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 7))

        progress = ctk.CTkProgressBar(
            row,
            height=10,
            corner_radius=8,
            fg_color=CARD_BG,
            progress_color=color
        )
        progress.pack(fill="x")
        progress.set(0 if total == 0 else count / total)

    def create_expiring_passwords_section(self, passwords_needing_update):
        ctk.CTkFrame(
            self.dashboard_summary_frame,
            height=1,
            fg_color=BORDER
        ).pack(fill="x", pady=(22, 18))

        ctk.CTkLabel(
            self.dashboard_summary_frame,
            text="Passwords Needing Update",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", pady=(0, 10))

        if not passwords_needing_update:
            ctk.CTkLabel(
                self.dashboard_summary_frame,
                text="No passwords need updating.",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 14)
            ).pack(anchor="w")
            return

        for website, username, age_days in passwords_needing_update:
            ctk.CTkLabel(
                self.dashboard_summary_frame,
                text=f"{website} — {username} — {age_days} days old",
                text_color=TEXT_PRIMARY,
                font=("Segoe UI", 14),
                justify="left",
                wraplength=680
            ).pack(anchor="w", pady=(0, 8))

    def create_favorites_section(self, favorites):
        ctk.CTkFrame(
            self.dashboard_summary_frame,
            height=1,
            fg_color=BORDER
        ).pack(fill="x", pady=(22, 18))

        ctk.CTkLabel(
            self.dashboard_summary_frame,
            text="⭐ Favorites",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", pady=(0, 10))

        if not favorites:
            ctk.CTkLabel(
                self.dashboard_summary_frame,
                text="No favorite passwords yet.",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 14)
            ).pack(anchor="w")
            return

        for _, website, username, _, _, _, _ in favorites:
            ctk.CTkLabel(
                self.dashboard_summary_frame,
                text=f"⭐ {website} — {username}",
                text_color=TEXT_PRIMARY,
                font=("Segoe UI", 14),
                justify="left",
                wraplength=680
            ).pack(anchor="w", pady=(0, 8))

    def create_reused_password_section(self, reused_groups):
        ctk.CTkFrame(
            self.dashboard_summary_frame,
            height=1,
            fg_color=BORDER
        ).pack(fill="x", pady=(22, 18))

        ctk.CTkLabel(
            self.dashboard_summary_frame,
            text="\u26a0 Reused Passwords",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", pady=(0, 10))

        if not reused_groups:
            ctk.CTkLabel(
                self.dashboard_summary_frame,
                text="No reused passwords found.",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 14)
            ).pack(anchor="w")
            return

        show_group_labels = len(reused_groups) > 1

        for index, accounts in enumerate(reused_groups, start=1):
            group_frame = ctk.CTkFrame(
                self.dashboard_summary_frame,
                corner_radius=16,
                fg_color=CARD_SOFT
            )
            group_frame.pack(fill="x", pady=(0, 10))

            if show_group_labels:
                ctk.CTkLabel(
                    group_frame,
                    text=f"Group {index}: {len(accounts)} accounts share one password",
                    text_color=TEXT_SECONDARY,
                    font=("Segoe UI", 12, "bold")
                ).pack(anchor="w", padx=16, pady=(14, 4))

            for website, username in accounts:
                ctk.CTkLabel(
                    group_frame,
                    text=f"- {website} \u2014 {username}",
                    text_color=TEXT_PRIMARY,
                    font=("Segoe UI", 14),
                    justify="left",
                    wraplength=680
                ).pack(anchor="w", padx=16, pady=(4, 10))

    def create_vault_view(self):
        self.vault_view = ctk.CTkFrame(self.main_area, fg_color="transparent")

        self.form_frame = ctk.CTkFrame(self.vault_view, width=360, corner_radius=24, fg_color=CARD_BG)
        self.form_frame.pack(side="left", fill="y", padx=(0, 22))
        self.form_frame.pack_propagate(False)

        ctk.CTkLabel(self.form_frame, text="Add Password", font=("Segoe UI", 23, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=26, pady=(26, 6))
        ctk.CTkLabel(self.form_frame, text="Save or update an account", font=("Segoe UI", 13), text_color=TEXT_MUTED).pack(anchor="w", padx=26, pady=(0, 22))

        self.website_entry = self.create_input(self.form_frame, "Website")
        self.website_entry.pack(fill="x", padx=26, pady=8)

        self.username_entry = self.create_input(self.form_frame, "Username / Email")
        self.username_entry.pack(fill="x", padx=26, pady=8)

        password_wrapper, self.password_entry = self.create_password_input_with_toggle(
            self.form_frame,
            "Password"
        )
        password_wrapper.pack(fill="x", padx=26, pady=8)
        self.password_entry.bind("<KeyRelease>", lambda event: self.update_strength())

        self.strength_label = ctk.CTkLabel(self.form_frame, text="Strength: -", text_color=TEXT_MUTED, font=("Segoe UI", 12))
        self.strength_label.pack(anchor="w", padx=26, pady=(4, 4))

        self.strength_bar = ctk.CTkProgressBar(self.form_frame, height=8, progress_color=ACCENT)
        self.strength_bar.pack(fill="x", padx=26, pady=(0, 10))
        self.strength_bar.set(0)

        self.note_entry = self.create_input(self.form_frame, "Note")
        self.note_entry.pack(fill="x", padx=26, pady=8)

        self.save_button = self.create_primary_button(self.form_frame, "Save / Update", self.save_password)
        self.save_button.pack(fill="x", padx=26, pady=(24, 10))

        self.generate_button = ctk.CTkButton(
            self.form_frame,
            text="Quick Generate",
            height=42,
            corner_radius=14,
            fg_color=CARD_SOFT,
            hover_color=CARD_SOFT_HOVER,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
            command=self.generate_password_quick
        )
        self.generate_button.pack(fill="x", padx=26, pady=8)

        self.table_frame = ctk.CTkFrame(self.vault_view, corner_radius=24, fg_color=CARD_BG)
        self.table_frame.pack(side="right", fill="both", expand=True)

        self.table_header = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.table_header.pack(fill="x", padx=24, pady=(24, 8))

        ctk.CTkLabel(self.table_header, text="Saved Passwords", font=("Segoe UI", 23, "bold"), text_color=TEXT_PRIMARY).pack(side="left")

        header_controls = ctk.CTkFrame(self.table_header, fg_color="transparent")
        header_controls.pack(side="right")

        self.count_label = ctk.CTkLabel(
            header_controls,
            text="0 items",
            font=("Segoe UI", 13),
            text_color=TEXT_MUTED
        )
        self.count_label.pack(side="right", padx=(14, 0))

        self.vault_view_mode_var = ctk.StringVar(
            value=get_vault_view_mode_label(self.vault_view_mode)
        )
        self.vault_view_mode_toggle = ctk.CTkSegmentedButton(
            header_controls,
            values=["Tiles", "List"],
            variable=self.vault_view_mode_var,
            width=150,
            height=34,
            corner_radius=12,
            border_width=2,
            fg_color=CARD_SOFT,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=CARD_SOFT,
            unselected_hover_color=CARD_SOFT_HOVER,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold"),
            command=self.change_vault_view_mode
        )
        self.vault_view_mode_toggle.pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(
            self.table_frame,
            fg_color="transparent",
            scrollbar_button_color=CARD_SOFT,
            scrollbar_button_hover_color=CARD_SOFT_HOVER
        )
        self.list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def create_generator_view(self):
        self.generator_view = ctk.CTkFrame(self.main_area, fg_color="transparent")

        card = ctk.CTkFrame(self.generator_view, corner_radius=24, fg_color=CARD_BG)
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(card, text="Password Generator", font=("Segoe UI", 30, "bold"), text_color=TEXT_PRIMARY).pack(anchor="w", padx=34, pady=(34, 8))
        ctk.CTkLabel(card, text="Generate strong passwords and send them directly to your vault form.", text_color=TEXT_SECONDARY, font=("Segoe UI", 14)).pack(anchor="w", padx=34, pady=(0, 28))

        self.generated_password_entry = self.create_input(card, "Generated password will appear here")
        self.generated_password_entry.configure(font=("Segoe UI", 18))
        self.generated_password_entry.pack(fill="x", padx=34, pady=(0, 26))

        self.length_label = ctk.CTkLabel(card, text="Length: 16", font=("Segoe UI", 14, "bold"), text_color=TEXT_PRIMARY)
        self.length_label.pack(anchor="w", padx=34)

        self.length_slider = ctk.CTkSlider(
            card,
            from_=8,
            to=32,
            number_of_steps=24,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            command=self.update_length_label
        )
        self.length_slider.set(16)
        self.length_slider.pack(fill="x", padx=34, pady=(10, 28))

        options = ctk.CTkFrame(card, fg_color="transparent")
        options.pack(fill="x", padx=34, pady=(0, 22))

        self.uppercase_var = ctk.BooleanVar(value=True)
        self.digits_var = ctk.BooleanVar(value=True)
        self.symbols_var = ctk.BooleanVar(value=True)

        for text, var in [("Uppercase letters", self.uppercase_var), ("Numbers", self.digits_var), ("Symbols", self.symbols_var)]:
            ctk.CTkCheckBox(options, text=text, variable=var, fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=TEXT_SECONDARY).pack(anchor="w", pady=7)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=34, pady=16)

        self.create_primary_button(btns, "Generate", self.generate_password_for_generator_page).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            btns,
            text="Use in Vault Form",
            height=46,
            corner_radius=14,
            fg_color=CARD_SOFT,
            hover_color=CARD_SOFT_HOVER,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold"),
            command=self.use_generated_password
        ).pack(side="left")

    def create_settings_view(self):
        self.settings_view = ctk.CTkScrollableFrame(
            self.main_area,
            fg_color="transparent",
            scrollbar_button_color=CARD_SOFT,
            scrollbar_button_hover_color=CARD_SOFT_HOVER
        )

        appearance_card = self.create_settings_card(self.settings_view, "Appearance")
        appearance_card.pack(fill="x", pady=(0, 24))

        theme_row = self.create_settings_row(
            appearance_card,
            "Theme",
            "Choose the app color preference."
        )
        self.theme_var = ctk.StringVar(value=get_theme_label(self.current_theme))
        self.theme_menu = self.create_settings_dropdown(
            theme_row,
            THEME_OPTIONS,
            self.theme_var,
            self.change_theme
        )
        self.theme_menu.pack(side="right")

        security_card = self.create_settings_card(self.settings_view, "Security")
        security_card.pack(fill="x", pady=(0, 24))

        change_password_row = self.create_settings_row(
            security_card,
            "Master Password",
            "Change the password used to unlock your vault."
        )
        ctk.CTkButton(
            change_password_row,
            text="Change Master Password",
            width=190,
            height=40,
            corner_radius=14,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 13, "bold"),
            command=self.open_change_master_password_modal
        ).pack(side="right")

        auto_lock_row = self.create_settings_row(
            security_card,
            "Auto Lock",
            "Lock the app after a period of inactivity."
        )
        self.auto_lock_var = ctk.BooleanVar(value=self.auto_lock_enabled)
        ctk.CTkSwitch(
            auto_lock_row,
            text="",
            variable=self.auto_lock_var,
            fg_color=CARD_SOFT,
            progress_color=ACCENT,
            button_color=TEXT_SECONDARY,
            button_hover_color=TEXT_PRIMARY,
            command=self.change_auto_lock_state
        ).pack(side="right")

        timeout_row = self.create_settings_row(
            security_card,
            "Timeout",
            "Choose when auto lock should activate."
        )
        self.timeout_var = ctk.StringVar(
            value=get_auto_lock_timeout_label(self.auto_lock_timeout_seconds)
        )
        self.timeout_menu = self.create_settings_dropdown(
            timeout_row,
            list(AUTO_LOCK_TIMEOUT_OPTIONS.keys()),
            self.timeout_var,
            self.change_auto_lock_timeout
        )
        self.timeout_menu.pack(side="right")

        data_card = self.create_settings_card(self.settings_view, "Data")
        data_card.pack(fill="x", pady=(0, 24))

        self.create_settings_action_button(
            data_card,
            "Export Database",
            self.export_database
        )
        self.create_settings_action_button(
            data_card,
            "Import Database",
            self.import_database
        )
        self.create_settings_action_button(
            data_card,
            "Create Backup",
            self.create_database_backup
        )

        about_card = self.create_settings_card(self.settings_view, "About")
        about_card.pack(fill="x")

        for item in [
            "SecurePass",
            "Version 1.0",
            "SQLite Database",
            "Fernet Encryption",
        ]:
            self.create_about_item(about_card, item)

    def create_settings_card(self, parent, title):
        card = ctk.CTkFrame(parent, corner_radius=24, fg_color=CARD_BG)

        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=26, pady=(24, 18))

        return card

    def create_settings_row(self, parent, title, description):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=26, pady=(0, 18))

        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=(0, 18))

        ctk.CTkLabel(
            text_frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_frame,
            text=description,
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(4, 0))

        return row

    def create_settings_dropdown(self, parent, values, variable, command=None):
        return ctk.CTkOptionMenu(
            parent,
            values=values,
            variable=variable,
            command=command,
            width=150,
            height=40,
            corner_radius=14,
            fg_color=INPUT_BG,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=CARD_SOFT,
            dropdown_hover_color=CARD_SOFT_HOVER,
            dropdown_text_color=TEXT_PRIMARY,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13)
        )

    def change_theme(self, selected_theme):
        theme = normalize_theme(selected_theme)
        ctk.set_appearance_mode(theme)
        database.set_setting(THEME_SETTING_KEY, theme)

        self.current_theme = theme
        self.theme_var.set(get_theme_label(theme))
        self.show_toast(f"Theme changed to {get_theme_label(theme)}")

    def change_auto_lock_state(self):
        self.auto_lock_enabled = bool(self.auto_lock_var.get())
        database.set_setting(
            AUTO_LOCK_ENABLED_SETTING_KEY,
            "1" if self.auto_lock_enabled else "0"
        )

        self.record_activity()
        self.schedule_auto_lock_check()

        if hasattr(self, "dashboard_view"):
            self.update_dashboard()

        if self.auto_lock_enabled:
            self.show_toast("Auto Lock enabled.")
        else:
            self.show_toast("Auto Lock disabled.")

    def change_auto_lock_timeout(self, selected_timeout):
        timeout_seconds = normalize_auto_lock_timeout(selected_timeout)
        self.auto_lock_timeout_seconds = timeout_seconds
        self.timeout_var.set(get_auto_lock_timeout_label(timeout_seconds))
        database.set_setting(AUTO_LOCK_TIMEOUT_SETTING_KEY, str(timeout_seconds))
        self.record_activity()
        self.schedule_auto_lock_check()

    def create_settings_action_button(self, parent, text, command):
        ctk.CTkButton(
            parent,
            text=text,
            height=44,
            corner_radius=14,
            fg_color=CARD_SOFT,
            hover_color=CARD_SOFT_HOVER,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
            command=command
        ).pack(fill="x", padx=26, pady=(0, 14))

    def create_about_item(self, parent, text):
        item = ctk.CTkFrame(parent, height=42, corner_radius=14, fg_color=CARD_SOFT)
        item.pack(fill="x", padx=26, pady=(0, 12))
        item.pack_propagate(False)

        ctk.CTkLabel(
            item,
            text=text,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left", padx=16)

    def create_database_backup(self):
        default_name = datetime.now().strftime("backup_%Y_%m_%d_%H_%M_%S.db")
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Create Backup",
            initialfile=default_name,
            defaultextension=".db",
            filetypes=[
                ("SQLite database", "*.db"),
                ("All files", "*.*"),
            ]
        )

        if not destination:
            return

        try:
            shutil.copy2(database.DB_FILE, destination)
        except Exception:
            messagebox.showerror(
                "Backup Failed",
                "Unable to create the database backup.",
                parent=self
            )
            return

        self.show_toast("Backup created successfully.")

    def export_database(self):
        if self.crypto is None:
            messagebox.showerror(
                "Vault Locked",
                "Unlock your vault before exporting passwords.",
                parent=self
            )
            return

        if not messagebox.askyesno(
            "Export Database",
            "Exported file will contain decrypted passwords. Continue?",
            parent=self
        ):
            return

        default_name = datetime.now().strftime("passwords_%Y_%m_%d_%H_%M_%S.csv")
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Export Database",
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
            ]
        )

        if not destination:
            return

        rows = database.get_passwords("", self.crypto)
        records = [
            {
                "website": website,
                "username": username,
                "password": password,
                "note": note or "",
                "updated_at": updated_at or "",
                "favorite": int(favorite or 0),
            }
            for _, website, username, password, note, updated_at, favorite in rows
        ]

        try:
            if destination.lower().endswith(".json"):
                self.write_password_json(destination, records)
            else:
                self.write_password_csv(destination, records)
        except Exception:
            messagebox.showerror(
                "Export Failed",
                "Unable to export password records.",
                parent=self
            )
            return

        self.show_toast("Database exported successfully.")

    def import_database(self):
        if self.crypto is None:
            messagebox.showerror(
                "Vault Locked",
                "Unlock your vault before importing passwords.",
                parent=self
            )
            return

        source = filedialog.askopenfilename(
            parent=self,
            title="Import Database",
            filetypes=[
                ("CSV and JSON files", ("*.csv", "*.json")),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
            ]
        )

        if not source:
            return

        try:
            if source.lower().endswith(".json"):
                records = self.read_password_json(source)
            else:
                records = self.read_password_csv(source)

            imported_count = self.save_imported_password_records(records)
        except Exception:
            messagebox.showerror(
                "Import Failed",
                "Unable to import password records.",
                parent=self
            )
            return

        if imported_count == 0:
            messagebox.showerror(
                "Import Failed",
                "No valid password records were found.",
                parent=self
            )
            return

        self.search_entry.delete(0, "end")
        self.load_passwords()
        self.update_dashboard()
        self.show_toast("Database imported successfully.")

    def write_password_csv(self, destination, records):
        fieldnames = ["website", "username", "password", "note", "updated_at", "favorite"]

        with open(destination, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    def write_password_json(self, destination, records):
        with open(destination, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=2)

    def read_password_csv(self, source):
        with open(source, "r", newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))

    def read_password_json(self, source):
        with open(source, "r", encoding="utf-8-sig") as file:
            data = json.load(file)

        if isinstance(data, dict):
            data = data.get("passwords", [])

        if not isinstance(data, list):
            raise ValueError("Imported JSON must contain a list of records.")

        return data

    def save_imported_password_records(self, records):
        imported_count = 0
        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        for record in records:
            if not isinstance(record, dict):
                continue

            website = str(record.get("website", "")).strip()
            username = str(record.get("username", "")).strip()
            password = (
                "" if record.get("password") is None
                else str(record.get("password"))
            )
            note = "" if record.get("note") is None else str(record.get("note"))
            updated_at = str(record.get("updated_at", "") or "").strip()
            favorite = 1 if setting_to_bool(record.get("favorite", "0")) else 0

            if not updated_at:
                updated_at = current_timestamp

            if not website or not username or not password:
                continue

            database.add_or_update_password(
                website,
                username,
                password,
                note,
                updated_at,
                self.crypto,
                favorite
            )
            imported_count += 1

        return imported_count

    def open_change_master_password_modal(self):
        if hasattr(self, "change_password_modal") and self.change_password_modal.winfo_exists():
            self.change_password_modal.focus()
            return

        modal_width = 430
        modal_height = 390

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - modal_width) // 2
        y = self.winfo_y() + (self.winfo_height() - modal_height) // 2

        modal = ctk.CTkToplevel(self)
        modal.title("Change Master Password")
        modal.geometry(f"{modal_width}x{modal_height}+{max(x, 0)}+{max(y, 0)}")
        modal.resizable(False, False)
        modal.configure(fg_color=APP_BG)
        modal.transient(self)
        modal.grab_set()
        self.change_password_modal = modal

        card = ctk.CTkFrame(modal, corner_radius=24, fg_color=CARD_BG)
        card.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            card,
            text="Change Master Password",
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=26, pady=(26, 6))

        ctk.CTkLabel(
            card,
            text="Your saved passwords will stay encrypted with the new key.",
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=26, pady=(0, 18))

        current_entry = self.create_input(card, "Current Master Password", show="•")
        current_entry.pack(fill="x", padx=26, pady=7)

        new_entry = self.create_input(card, "New Master Password", show="•")
        new_entry.pack(fill="x", padx=26, pady=7)

        confirm_entry = self.create_input(card, "Confirm New Master Password", show="•")
        confirm_entry.pack(fill="x", padx=26, pady=7)

        def submit_change():
            self.change_master_password(
                current_entry.get().strip(),
                new_entry.get().strip(),
                confirm_entry.get().strip(),
                modal
            )

        for entry in [current_entry, new_entry, confirm_entry]:
            entry.bind("<Return>", lambda event: submit_change())

        button_row = ctk.CTkFrame(card, fg_color="transparent")
        button_row.pack(fill="x", padx=26, pady=(24, 0))

        ctk.CTkButton(
            button_row,
            text="Cancel",
            width=118,
            height=42,
            corner_radius=14,
            fg_color=CARD_SOFT,
            hover_color=CARD_SOFT_HOVER,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
            command=modal.destroy
        ).pack(side="left")

        ctk.CTkButton(
            button_row,
            text="Change Password",
            width=180,
            height=42,
            corner_radius=14,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            font=("Segoe UI", 13, "bold"),
            command=submit_change
        ).pack(side="right")

        current_entry.focus_set()

    def change_master_password(self, current_password, new_password, confirm_password, modal):
        if not current_password or not new_password or not confirm_password:
            messagebox.showerror("Missing Information", "Please fill all fields.", parent=modal)
            return

        if len(new_password) < 6:
            messagebox.showerror("Weak Password", "New master password must be at least 6 characters.", parent=modal)
            return

        if new_password != confirm_password:
            messagebox.showerror("Password Mismatch", "New master password and confirmation do not match.", parent=modal)
            return

        if not database.verify_master_password(current_password):
            messagebox.showerror("Access Denied", "Current master password is incorrect.", parent=modal)
            return

        try:
            old_crypto = database.create_crypto(current_password)
            encrypted_rows = database.get_encrypted_password_rows()

            decrypted_rows = []
            for row in encrypted_rows:
                password_id, website, username, encrypted_password, note, updated_at, favorite = row
                password = database.decrypt_password_strict(old_crypto, encrypted_password)
                decrypted_rows.append((password_id, website, username, password, note, updated_at, favorite))

            master_password_value, new_crypto = database.create_master_password_value_and_crypto(new_password)

            reencrypted_rows = []
            for password_id, website, username, password, note, updated_at, favorite in decrypted_rows:
                encrypted_password = database.encrypt_password(new_crypto, password)
                reencrypted_rows.append((password_id, website, username, encrypted_password, note, updated_at, favorite))

            database.replace_master_password_and_password_rows(master_password_value, reencrypted_rows)
        except Exception:
            messagebox.showerror(
                "Change Failed",
                "Unable to change master password. Existing vault data was left unchanged.",
                parent=modal
            )
            return

        self.crypto = new_crypto
        modal.destroy()
        self.load_passwords()
        self.update_dashboard()
        self.show_toast("Master password changed successfully.")

    def hide_all_views(self):
        for view_name in ["dashboard_view", "vault_view", "generator_view", "settings_view"]:
            if hasattr(self, view_name):
                getattr(self, view_name).pack_forget()

    def show_dashboard(self):
        self.hide_all_views()
        self.dashboard_view.pack(fill="both", expand=True, padx=34, pady=22)
        self.page_title.configure(text="Dashboard")
        self.search_entry.pack_forget()
        self.set_active_nav("dashboard")
        self.update_dashboard(animate=True)

    def show_vault(self):
        self.hide_all_views()
        self.vault_view.pack(fill="both", expand=True, padx=34, pady=22)
        self.page_title.configure(text="Vault")

        if not self.search_entry.winfo_ismapped():
            self.search_entry.pack(side="right")

        self.set_active_nav("vault")
        self.load_passwords()

    def show_generator(self):
        self.hide_all_views()
        self.generator_view.pack(fill="both", expand=True, padx=34, pady=22)
        self.page_title.configure(text="Generator")
        self.search_entry.pack_forget()
        self.set_active_nav("generator")

    def show_settings(self):
        self.hide_all_views()
        self.settings_view.pack(fill="both", expand=True, padx=34, pady=22)
        self.page_title.configure(text="Settings")
        self.search_entry.pack_forget()
        self.set_active_nav("settings")

    def change_vault_view_mode(self, selected_mode):
        view_mode = normalize_vault_view_mode(selected_mode)

        if view_mode == self.vault_view_mode:
            return

        self.vault_view_mode = view_mode
        self.vault_view_mode_var.set(get_vault_view_mode_label(view_mode))
        database.set_setting(VAULT_VIEW_MODE_SETTING_KEY, view_mode)
        self.load_passwords()

    def save_password(self):
        editing_password_id = self.editing_password_id
        favorite = 0

        website = self.website_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        note = self.note_entry.get().strip()
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not website or not username or not password:
            messagebox.showerror("Missing Information", "Website, username and password are required.")
            return

        if editing_password_id is not None:
            favorite = database.get_password_favorite(editing_password_id)
            database.delete_password(editing_password_id)
            self.editing_password_id = None
            self.save_button.configure(text="Save Password")

        database.add_or_update_password(
            website,
            username,
            password,
            note,
            updated_at,
            self.crypto,
            favorite
        )

        self.clear_form()
        self.load_passwords()
        self.update_dashboard()

        self.show_toast("Password saved or updated successfully.")

    def load_passwords(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        search_text = self.search_entry.get().strip()
        passwords = database.get_passwords(search_text, self.crypto)

        self.count_label.configure(text=f"{len(passwords)} items")

        if not passwords:
            ctk.CTkLabel(self.list_frame, text="No passwords found.", text_color=TEXT_MUTED, font=("Segoe UI", 14)).pack(pady=36)
            return

        favorites = [item for item in passwords if item[-1]]
        regular_passwords = [item for item in passwords if not item[-1]]
        item_renderer = (
            self.create_password_list_row
            if self.vault_view_mode == "list"
            else self.create_password_card
        )

        if favorites:
            self.create_vault_section_header("⭐ Favorites")

            for item in favorites:
                item_renderer(item)

            if regular_passwords:
                self.create_vault_divider()

        for item in regular_passwords:
            item_renderer(item)

    def create_vault_section_header(self, title):
        ctk.CTkLabel(
            self.list_frame,
            text=title,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=12, pady=(4, 6))

    def create_vault_divider(self):
        ctk.CTkFrame(
            self.list_frame,
            height=1,
            fg_color=BORDER
        ).pack(fill="x", padx=8, pady=(8, 16))

    def get_password_health(self, password):
        score = self.calculate_strength(password)

        if score >= 4:
            level = "Strong"
        elif score == 3:
            level = "Medium"
        else:
            level = "Weak"

        style = PASSWORD_HEALTH_STYLES[level]
        reason = style.get("reason")

        if reason is None:
            weak_reasons = []

            if len(password) < 8:
                weak_reasons.append("too short")
            if not any(c in "!@#$%^&*" for c in password):
                weak_reasons.append("missing symbols")
            if not any(c.isdigit() for c in password):
                weak_reasons.append("missing numbers")
            if not any(c.isupper() for c in password):
                weak_reasons.append("missing uppercase")
            if not any(c.islower() for c in password):
                weak_reasons.append("missing lowercase")

            reason = ", ".join(weak_reasons[:2]).capitalize() if weak_reasons else "Needs more variety"

        return level, style["bg"], style["text"], reason

    def get_password_sha1_hash(self, password):
        return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()

    def get_exposure_checking_status(self, password_hash):
        return {
            "state": "checking",
            "count": 0,
            "password_hash": password_hash,
        }

    def get_exposure_failed_status(self, password_hash=None):
        return {
            "state": "failed",
            "count": 0,
            "password_hash": password_hash,
        }

    def get_exposure_status(self, password):
        if password in {"[locked]", "[decryption failed]"}:
            return self.get_exposure_failed_status()

        password_hash = self.get_password_sha1_hash(password)
        status = self.exposure_statuses.get(password_hash)

        if status is None:
            return self.get_exposure_checking_status(password_hash)

        return status

    def get_exposure_display(self, status):
        state = status.get("state", "not_checked")
        style = EXPOSURE_STATUS_STYLES.get(
            state,
            EXPOSURE_STATUS_STYLES["not_checked"]
        )
        detail = style["detail"].format(count=status.get("count", 0))

        return style["label"], detail, style["bg"], style["text"]

    def widget_exists(self, widget):
        try:
            return widget is not None and widget.winfo_exists()
        except Exception:
            return False

    def configure_exposure_widgets(self, status_label, detail_label, status):
        label, detail, bg_color, text_color = self.get_exposure_display(status)

        if self.widget_exists(status_label):
            status_label.configure(
                text=label,
                fg_color=bg_color,
                text_color=text_color
            )

        if self.widget_exists(detail_label):
            detail_label.configure(
                text=detail,
                text_color=text_color if detail else TEXT_MUTED
            )

    def fetch_exposure_count(self, password_hash):
        prefix = password_hash[:5]
        suffix = password_hash[5:]
        request = urllib.request.Request(
            HIBP_RANGE_URL.format(prefix=prefix),
            headers={
                "Add-Padding": "true",
                "User-Agent": "SecurePass-Password-Manager",
            }
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError("Unexpected HIBP response")

            body = response.read().decode("utf-8")

        for line in body.splitlines():
            try:
                returned_suffix, count = line.split(":", 1)
            except ValueError:
                continue

            if returned_suffix.upper() == suffix:
                return int(count)

        return 0

    def start_password_exposure_check(self, password, status_label, detail_label):
        if password in {"[locked]", "[decryption failed]"}:
            self.configure_exposure_widgets(
                status_label,
                detail_label,
                self.get_exposure_failed_status()
            )
            return

        password_hash = self.get_password_sha1_hash(password)
        cached_status = self.exposure_statuses.get(password_hash)

        if cached_status is not None:
            self.configure_exposure_widgets(status_label, detail_label, cached_status)
            return

        self.exposure_pending_widgets.setdefault(password_hash, []).append(
            (status_label, detail_label)
        )
        self.configure_exposure_widgets(
            status_label,
            detail_label,
            self.get_exposure_checking_status(password_hash)
        )

        if password_hash in self.exposure_checks_in_flight:
            return

        self.exposure_checks_in_flight.add(password_hash)
        threading.Thread(
            target=lambda: self.run_exposure_check(password_hash),
            daemon=True
        ).start()

    def run_exposure_check(self, password_hash):
        try:
            breach_count = self.fetch_exposure_count(password_hash)
            succeeded = True
        except Exception:
            breach_count = 0
            succeeded = False

        try:
            self.after(
                0,
                lambda: self.finish_exposure_check(
                    password_hash,
                    breach_count,
                    succeeded
                )
            )
        except Exception:
            pass

    def finish_exposure_check(
        self,
        password_hash,
        breach_count,
        succeeded
    ):
        self.exposure_checks_in_flight.discard(password_hash)

        if not succeeded:
            status = self.get_exposure_failed_status(password_hash)
        else:
            status = {
                "state": "exposed" if breach_count > 0 else "safe",
                "count": breach_count,
                "password_hash": password_hash,
            }

        self.exposure_statuses[password_hash] = status

        pending_widgets = self.exposure_pending_widgets.pop(password_hash, [])
        for status_label, detail_label in pending_widgets:
            self.configure_exposure_widgets(status_label, detail_label, status)

        if hasattr(self, "dashboard_view"):
            self.update_dashboard()

    def create_password_list_row(self, item):
        password_id, website, username, password, note, updated_at, favorite = item

        row = ctk.CTkFrame(
            self.list_frame,
            height=82,
            corner_radius=16,
            fg_color=CARD_SOFT
        )
        row.pack(fill="x", pady=5, padx=6)
        row.pack_propagate(False)

        ctk.CTkButton(
            row,
            text="⭐" if favorite else "☆",
            width=36,
            height=34,
            corner_radius=10,
            fg_color=FAVORITE_BUTTON_BG if favorite else "transparent",
            hover_color=FAVORITE_BUTTON_HOVER if favorite else CARD_SOFT_HOVER,
            text_color=FAVORITE_BUTTON_TEXT if favorite else TEXT_SECONDARY,
            font=("Segoe UI", 16, "bold"),
            command=lambda: self.toggle_favorite(password_id)
        ).pack(side="left", padx=(12, 8), pady=24)

        actions = ctk.CTkFrame(
            row,
            width=116,
            height=58,
            fg_color="transparent"
        )
        actions.pack(side="right", padx=(8, 12), pady=12)
        actions.pack_propagate(False)
        actions.grid_propagate(False)

        action_font = ("Segoe UI", 10, "bold")

        show_button = ctk.CTkButton(
            actions,
            text="Show",
            width=52,
            height=25,
            corner_radius=8,
            fg_color=NEUTRAL_BUTTON_BG,
            hover_color=NEUTRAL_BUTTON_HOVER,
            text_color=TEXT_PRIMARY,
            font=action_font,
            command=lambda: self.toggle_password(password_label, password, show_button)
        )
        show_button.grid(row=0, column=0, padx=2, pady=2)

        ctk.CTkButton(
            actions,
            text="Copy",
            width=52,
            height=25,
            corner_radius=8,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            font=action_font,
            command=lambda: self.copy_password(password)
        ).grid(row=0, column=1, padx=2, pady=2)

        ctk.CTkButton(
            actions,
            text="Edit",
            width=52,
            height=25,
            corner_radius=8,
            fg_color="#0ea5e9",
            hover_color="#0284c7",
            text_color=TEXT_ON_ACCENT,
            font=action_font,
            command=lambda: self.edit_password(
                password_id,
                website,
                username,
                password,
                note
            )
        ).grid(row=1, column=0, padx=2, pady=2)

        ctk.CTkButton(
            actions,
            text="Delete",
            width=52,
            height=25,
            corner_radius=8,
            fg_color="transparent",
            hover_color=DANGER_HOVER,
            text_color=DANGER_TEXT,
            font=action_font,
            command=lambda: self.delete_password(password_id)
        ).grid(row=1, column=1, padx=2, pady=2)

        details = ctk.CTkFrame(row, fg_color="transparent")
        details.pack(side="left", fill="both", expand=True, pady=9)

        top_line = ctk.CTkFrame(details, fg_color="transparent")
        top_line.pack(fill="x")

        ctk.CTkLabel(
            top_line,
            text=website,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", anchor="w")

        ctk.CTkLabel(
            top_line,
            text=username,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 12)
        ).pack(side="left", padx=(14, 0), anchor="w")

        password_label = ctk.CTkLabel(
            top_line,
            text="•" * len(password),
            text_color=TEXT_MUTED,
            font=("Segoe UI", 12)
        )
        password_label.pack(side="left", padx=(14, 0), anchor="w")

        health_label, health_bg, health_text, _ = self.get_password_health(password)
        exposure_status = self.get_exposure_status(password)
        exposure_label, _, exposure_bg, exposure_text = self.get_exposure_display(exposure_status)
        age_days = get_password_age_days(updated_at)
        password_age_value = format_password_age_value(age_days)
        password_age_color = get_password_age_color(age_days)

        status_row = ctk.CTkFrame(details, fg_color="transparent")
        status_row.pack(anchor="w", pady=(8, 0))

        ctk.CTkLabel(
            status_row,
            text=health_label,
            width=66,
            height=23,
            corner_radius=11,
            fg_color=health_bg,
            text_color=health_text,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        exposure_status_label = ctk.CTkLabel(
            status_row,
            text=exposure_label,
            width=108,
            height=23,
            corner_radius=11,
            fg_color=exposure_bg,
            text_color=exposure_text,
            font=("Segoe UI", 10, "bold")
        )
        exposure_status_label.pack(side="left", padx=(7, 0))

        ctk.CTkLabel(
            status_row,
            text=f"Age {password_age_value}",
            width=92,
            height=23,
            corner_radius=11,
            fg_color=INPUT_BG,
            text_color=password_age_color,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(7, 0))

        self.start_password_exposure_check(
            password,
            exposure_status_label,
            None
        )

    def create_password_card(self, item):
        password_id, website, username, password, note, updated_at, favorite = item

        card = ctk.CTkFrame(
            self.list_frame,
            corner_radius=20,
            fg_color=CARD_SOFT
        )
        card.pack(fill="x", pady=9, padx=6)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            left,
            text=website,
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=username,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 13)
        ).pack(anchor="w", pady=(6, 0))

        password_label = ctk.CTkLabel(
            left,
            text="•" * len(password),
            text_color=TEXT_MUTED,
            font=("Segoe UI", 13)
        )
        password_label.pack(anchor="w", pady=(6, 0))

        health_label, health_bg, health_text, health_reason = self.get_password_health(password)
        exposure_status = self.get_exposure_status(password)
        exposure_label, exposure_detail, exposure_bg, exposure_text = self.get_exposure_display(exposure_status)
        age_days = get_password_age_days(updated_at)
        password_age_value = format_password_age_value(age_days)
        password_age_color = get_password_age_color(age_days)

        badge_row = ctk.CTkFrame(left, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(10, 0))

        ctk.CTkLabel(
            badge_row,
            text=health_label,
            width=74,
            height=24,
            corner_radius=12,
            fg_color=health_bg,
            text_color=health_text,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

        exposure_status_label = ctk.CTkLabel(
            badge_row,
            text=exposure_label,
            width=112,
            height=24,
            corner_radius=12,
            fg_color=exposure_bg,
            text_color=exposure_text,
            font=("Segoe UI", 11, "bold")
        )
        exposure_status_label.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            left,
            text=health_reason,
            text_color=health_text,
            font=("Segoe UI", 12)
        ).pack(anchor="w", pady=(4, 0))

        exposure_detail_label = ctk.CTkLabel(
            left,
            text=exposure_detail,
            text_color=exposure_text if exposure_detail else TEXT_MUTED,
            font=("Segoe UI", 12)
        )
        exposure_detail_label.pack(anchor="w", pady=(4, 0))
        self.start_password_exposure_check(
            password,
            exposure_status_label,
            exposure_detail_label
        )

        if note:
            ctk.CTkLabel(
                left,
                text=note,
                text_color=TEXT_MUTED,
                font=("Segoe UI", 12)
            ).pack(anchor="w", pady=(6, 0))

        password_age_frame = ctk.CTkFrame(left, fg_color="transparent")
        password_age_frame.pack(anchor="w", pady=(8, 0))

        ctk.CTkLabel(
            password_age_frame,
            text="Password Age",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 11)
        ).pack(anchor="w")

        ctk.CTkLabel(
            password_age_frame,
            text=password_age_value,
            text_color=password_age_color,
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w", pady=(1, 0))

        if age_days is not None and age_days >= PASSWORD_UPDATE_THRESHOLD_DAYS:
            ctk.CTkLabel(
                left,
                text="\u26a0 Change this password",
                text_color=DANGER_TEXT,
                font=("Segoe UI", 12, "bold")
            ).pack(anchor="w", pady=(6, 0))

            ctk.CTkLabel(
                left,
                text="Recommendation: Update this password.",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 12)
            ).pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=18, pady=12)

        favorite_button = ctk.CTkButton(
            right,
            text="⭐" if favorite else "☆",
            width=76,
            height=32,
            corner_radius=10,
            fg_color=FAVORITE_BUTTON_BG if favorite else "transparent",
            hover_color=FAVORITE_BUTTON_HOVER if favorite else CARD_SOFT_HOVER,
            text_color=FAVORITE_BUTTON_TEXT if favorite else TEXT_SECONDARY,
            font=("Segoe UI", 16, "bold"),
            command=lambda: self.toggle_favorite(password_id)
        )
        favorite_button.pack(pady=3)

        show_button = ctk.CTkButton(
            right,
            text="Show",
            width=76,
            height=32,
            corner_radius=10,
            fg_color=NEUTRAL_BUTTON_BG,
            hover_color=NEUTRAL_BUTTON_HOVER,
            text_color=TEXT_PRIMARY,
            command=lambda: self.toggle_password(password_label, password, show_button)
        )
        show_button.pack(pady=3)

        ctk.CTkButton(
            right,
            text="Copy",
            width=76,
            height=32,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_ON_ACCENT,
            command=lambda: self.copy_password(password)
        ).pack(pady=3)

        ctk.CTkButton(
            right,
            text="Edit",
            width=76,
            height=32,
            corner_radius=10,
            fg_color="#0ea5e9",
            hover_color="#0284c7",
            text_color=TEXT_ON_ACCENT,
            command=lambda: self.edit_password(
                password_id,
                website,
                username,
                password,
                note
            )
        ).pack(pady=3)

        ctk.CTkButton(
            right,
            text="Delete",
            width=76,
            height=32,
            corner_radius=10,
            fg_color="transparent",
            hover_color=DANGER_HOVER,
            text_color=DANGER_TEXT,
            command=lambda: self.delete_password(password_id)
        ).pack(pady=3)

    def toggle_favorite(self, password_id):
        favorite = database.toggle_favorite(password_id)

        if favorite is None:
            messagebox.showerror("Favorite Error", "Unable to update favorite status.")
            return

        self.load_passwords()
        self.update_dashboard()
        self.show_toast(
            "Added to favorites" if favorite else "Removed from favorites"
        )

    def edit_password(self, password_id, website, username, password, note):
        self.editing_password_id = password_id

        self.website_entry.delete(0, "end")
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.note_entry.delete(0, "end")

        self.website_entry.insert(0, website)
        self.username_entry.insert(0, username)
        self.password_entry.insert(0, password)
        self.note_entry.insert(0, note)

        self.save_button.configure(text="Update Password")

        self.show_vault()

    def toggle_password(self, label, password, button):
        if "•" in label.cget("text"):
            label.configure(text=password)
            button.configure(text="Hide")
        else:
            label.configure(text="•" * len(password))
            button.configure(text="Show")

    def copy_password(self, password):
        self.clipboard_clear()
        self.clipboard_append(password)
        self.show_toast("Password copied to clipboard.")

    def delete_password(self, password_id):
        if not messagebox.askyesno("Delete", "Are you sure you want to delete this password?"):
            return

        database.delete_password(password_id)
        self.load_passwords()
        self.update_dashboard()
        self.show_toast("Password deleted successfully.")

    def update_strength(self):
        password = self.password_entry.get()
        score = self.calculate_strength(password)

        self.strength_bar.set(score / 5)

        if not password:
            self.strength_label.configure(text="Strength: -", text_color=TEXT_MUTED)
            return

        if score <= 1:
            self.strength_label.configure(text="Strength: Weak", text_color="#ef4444")
        elif score <= 3:
            self.strength_label.configure(text="Strength: Medium", text_color="#f59e0b")
        else:
            self.strength_label.configure(text="Strength: Strong", text_color="#22c55e")

    def calculate_strength(self, password):
        score = 0

        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*" for c in password):
            score += 1

        return min(score, 5)

    def generate_password_quick(self):
        generated = self.create_random_password(16, True, True, True)
        self.password_entry.configure(show="•")
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, generated)
        self.update_strength()

    def update_length_label(self, value):
        self.length_label.configure(text=f"Length: {int(value)}")

    def generate_password_for_generator_page(self):
        generated = self.create_random_password(
            int(self.length_slider.get()),
            self.uppercase_var.get(),
            self.digits_var.get(),
            self.symbols_var.get()
        )

        if not generated:
            messagebox.showerror("Generator Error", "Please select at least one character type.")
            return

        self.generated_password_entry.delete(0, "end")
        self.generated_password_entry.insert(0, generated)

    def create_random_password(self, length, use_uppercase, use_digits, use_symbols):
        characters = string.ascii_lowercase

        if use_uppercase:
            characters += string.ascii_uppercase

        if use_digits:
            characters += string.digits

        if use_symbols:
            characters += "!@#$%^&*"

        if not characters:
            return ""

        return "".join(random.choice(characters) for _ in range(length))

    def use_generated_password(self):
        generated = self.generated_password_entry.get().strip()

        if not generated:
            messagebox.showerror("No Password", "Please generate a password first.")
            return

        self.password_entry.configure(show="•")
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, generated)
        self.update_strength()
        self.show_vault()

    def clear_form(self):
        if not hasattr(self, "website_entry"):
            return

        self.website_entry.delete(0, "end")
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.note_entry.delete(0, "end")

        self.website_entry.configure(placeholder_text="Website")
        self.username_entry.configure(placeholder_text="Username / Email")
        self.password_entry.configure(placeholder_text="Password", show="•")
        self.note_entry.configure(placeholder_text="Note")

        self.strength_bar.set(0)
        self.strength_label.configure(text="Strength: -", text_color=TEXT_MUTED)

        self.focus()

    def toggle_entry_visibility(self, entry, button):
        if entry.cget("show") == "•":
            entry.configure(show="")
            button.configure(text="🙈")
        else:
            entry.configure(show="•")
            button.configure(text="👁")
    
    def create_password_input_with_toggle(self, parent, placeholder, width=240):
        wrapper = ctk.CTkFrame(
            parent,
            fg_color=INPUT_BG,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )

        entry = ctk.CTkEntry(
            wrapper,
            placeholder_text=placeholder,
            show="•",
            height=44,
            border_width=0,
            fg_color=INPUT_BG,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            font=("Segoe UI", 13)
        )
        entry.pack(side="left", fill="both", expand=True, padx=(10, 0))

        button = ctk.CTkButton(
            wrapper,
            text="👁",
            width=42,
            height=36,
            fg_color="transparent",
            hover_color=CARD_SOFT,
            text_color=TEXT_SECONDARY,
            command=lambda: self.toggle_entry_visibility(entry, button)
        )
        button.pack(side="right", padx=(0, 6))

        return wrapper, entry


if __name__ == "__main__":
    app = SecurePassApp()
    app.mainloop()
