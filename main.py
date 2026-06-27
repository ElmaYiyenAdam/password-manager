import customtkinter as ctk
from tkinter import filedialog, messagebox
import csv
import json
import random
import shutil
import string
import time
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

APP_BG = ("#f1f5f9", "#0f172a")
SIDEBAR_BG = ("#ffffff", "#020617")
CARD_BG = ("#ffffff", "#111827")
CARD_SOFT = ("#e2e8f0", "#1f2937")
CARD_SOFT_HOVER = ("#cbd5e1", "#334155")
NEUTRAL_BUTTON_BG = ("#f8fafc", "#334155")
NEUTRAL_BUTTON_HOVER = ("#e2e8f0", "#475569")
INPUT_BG = ("#f8fafc", "#0b1220")

TEXT_PRIMARY = ("#0f172a", "#f8fafc")
TEXT_SECONDARY = ("#334155", "#94a3b8")
TEXT_MUTED = ("#64748b", "#64748b")
TEXT_ON_ACCENT = "#ffffff"

ACCENT = "#7c3aed"
ACCENT_HOVER = "#6d28d9"

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


def load_saved_theme():
    database.create_table()
    theme = normalize_theme(database.get_setting(THEME_SETTING_KEY, DEFAULT_THEME))
    ctk.set_appearance_mode(theme)
    return theme


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
        super().__init__()

        self.current_theme = initial_theme
        self.auto_lock_enabled = auto_lock_enabled
        self.auto_lock_timeout_seconds = auto_lock_timeout_seconds
        self.auto_lock_after_id = None
        self.last_activity_time = time.monotonic()
        self.editing_password_id = None
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

        for widget in self.winfo_children():
            widget.destroy()
        self.toast = None

    def show_toast(self, message, kind="success"):
        colors = {
            "success": {
                "bg": "#14532d",
                "border": "#22c55e",
                "text": "#dcfce7",
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
        self.dashboard_view = ctk.CTkFrame(self.main_area, fg_color="transparent")

        top = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        top.pack(fill="x")

        self.total_card = self.create_stat_card(top, "Total Passwords", "0", "#60a5fa")
        self.total_card.pack(side="left", fill="both", expand=True, padx=(0, 14))

        self.strong_card = self.create_stat_card(top, "Strong", "0", "#22c55e")
        self.strong_card.pack(side="left", fill="both", expand=True, padx=7)

        self.weak_card = self.create_stat_card(top, "Weak", "0", "#ef4444")
        self.weak_card.pack(side="left", fill="both", expand=True, padx=7)

        self.reused_card = self.create_stat_card(top, "Reused", "0", "#f59e0b")
        self.reused_card.pack(side="left", fill="both", expand=True, padx=(14, 0))

        bottom = ctk.CTkFrame(self.dashboard_view, corner_radius=24, fg_color=CARD_BG)
        bottom.pack(fill="both", expand=True, pady=(24, 0))

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

        self.dashboard_summary_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        self.dashboard_summary_frame.pack(fill="both", expand=True, padx=26, pady=(0, 24))

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

    def update_dashboard(self):
        rows = database.get_passwords("", self.crypto)

        total = len(rows)
        strong = 0
        weak = 0

        accounts_by_password = {}

        for row in rows:
            _, website, username, password, _, _ = row

            if password == "[decryption failed]" or password == "[locked]":
                continue

            accounts_by_password.setdefault(password, []).append((website, username))

            score = self.calculate_strength(password)
            if score >= 4:
                strong += 1
            elif score <= 2:
                weak += 1

        reused_groups = [
            accounts
            for accounts in accounts_by_password.values()
            if len(accounts) > 1
        ]
        reused = sum(len(accounts) for accounts in reused_groups)

        self.total_card.value_label.configure(text=str(total))
        self.strong_card.value_label.configure(text=str(strong))
        self.weak_card.value_label.configure(text=str(weak))
        self.reused_card.value_label.configure(text=str(reused))

        for widget in self.dashboard_summary_frame.winfo_children():
            widget.destroy()

        if total == 0:
            ctk.CTkLabel(
                self.dashboard_summary_frame,
                text="No passwords saved yet. Add your first password from the Vault page.",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 15)
            ).pack(anchor="w", pady=10)
            self.create_reused_password_section(reused_groups)
            return

        security_text = "Your vault looks healthy."
        security_color = "#22c55e"

        if weak > 0 or reused > 0:
            security_text = "Some passwords need attention."
            security_color = "#f59e0b"

        if weak >= 3 or reused >= 3:
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
            text=f"{strong} strong passwords, {weak} weak passwords, {reused} reused password entries.",
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 14)
        ).pack(anchor="w")

        self.create_reused_password_section(reused_groups)

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

        self.count_label = ctk.CTkLabel(self.table_header, text="0 items", font=("Segoe UI", 13), text_color=TEXT_MUTED)
        self.count_label.pack(side="right")

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
            }
            for _, website, username, password, note, updated_at in rows
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
        fieldnames = ["website", "username", "password", "note", "updated_at"]

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
                self.crypto
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
                password_id, website, username, encrypted_password, note, updated_at = row
                password = database.decrypt_password_strict(old_crypto, encrypted_password)
                decrypted_rows.append((password_id, website, username, password, note, updated_at))

            master_password_value, new_crypto = database.create_master_password_value_and_crypto(new_password)

            reencrypted_rows = []
            for password_id, website, username, password, note, updated_at in decrypted_rows:
                encrypted_password = database.encrypt_password(new_crypto, password)
                reencrypted_rows.append((password_id, website, username, encrypted_password, note, updated_at))

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
        self.update_dashboard()

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

    def save_password(self):
        if self.editing_password_id is not None:
            database.delete_password(self.editing_password_id)
            self.editing_password_id = None
            self.save_button.configure(text="Save Password")
        website = self.website_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        note = self.note_entry.get().strip()
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not website or not username or not password:
            messagebox.showerror("Missing Information", "Website, username and password are required.")
            return

        database.add_or_update_password(website, username, password, note, updated_at, self.crypto)

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

        for item in passwords:
            self.create_password_card(item)

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

    def create_password_card(self, item):
        password_id, website, username, password, note, updated_at = item

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

        ctk.CTkLabel(
            left,
            text=health_label,
            width=74,
            height=24,
            corner_radius=12,
            fg_color=health_bg,
            text_color=health_text,
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(10, 0))

        ctk.CTkLabel(
            left,
            text=health_reason,
            text_color=health_text,
            font=("Segoe UI", 12)
        ).pack(anchor="w", pady=(4, 0))

        if note:
            ctk.CTkLabel(
                left,
                text=note,
                text_color=TEXT_MUTED,
                font=("Segoe UI", 12)
            ).pack(anchor="w", pady=(6, 0))

        if updated_at:
            ctk.CTkLabel(
                left,
                text=f"Updated {updated_at}",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 12)
            ).pack(anchor="w", pady=(6, 0))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=18, pady=12)

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
