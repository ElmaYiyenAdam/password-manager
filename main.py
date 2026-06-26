import customtkinter as ctk
from tkinter import messagebox
import random
import string
from datetime import datetime
import database

ctk.set_appearance_mode("dark")

APP_BG = "#0f172a"
SIDEBAR_BG = "#020617"
CARD_BG = "#111827"
CARD_SOFT = "#1f2937"
INPUT_BG = "#0b1220"

TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"

ACCENT = "#7c3aed"
ACCENT_HOVER = "#6d28d9"

DANGER_HOVER = "#991b1b"
BORDER = "#334155"


class SecurePassApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        database.create_table()

        self.title("SecurePass Manager")
        self.geometry("1120x700")
        self.minsize(1000, 620)
        self.configure(fg_color=APP_BG)
        self.crypto = None

        if database.has_master_password():
            self.create_unlock_screen()
        else:
            self.create_master_setup_screen()

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def create_master_setup_screen(self):
        self.clear_window()
        self.configure(fg_color=APP_BG)

        container = ctk.CTkFrame(self, width=430, height=360, corner_radius=24, fg_color=CARD_BG)
        container.pack(expand=True)
        container.pack_propagate(False)

        ctk.CTkLabel(
            container,
            text="SecurePass",
            font=("Segoe UI", 32, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(45, 6))

        ctk.CTkLabel(
            container,
            text="Create your master password",
            font=("Segoe UI", 14),
            text_color=TEXT_SECONDARY
        ).pack(pady=(0, 28))

        self.master_password_entry = self.create_input(
            container,
            "Master Password",
            show="•",
            width=310
        )
        self.master_password_entry.pack(pady=8)

        self.confirm_master_entry = self.create_input(
            container,
            "Confirm Master Password",
            show="•",
            width=310
        )
        self.confirm_master_entry.pack(pady=8)
        
        self.confirm_master_entry.bind(
            "<Return>",
            lambda event: self.save_master_password()
        )

        ctk.CTkButton(
            container,
            text="Create Vault",
            width=310,
            height=46,
            corner_radius=14,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
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

        container = ctk.CTkFrame(self, width=430, height=300, corner_radius=24, fg_color=CARD_BG)
        container.pack(expand=True)
        container.pack_propagate(False)

        ctk.CTkLabel(
            container,
            text="SecurePass",
            font=("Segoe UI", 34, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(55, 8))

        ctk.CTkLabel(
            container,
            text="Unlock your password vault",
            font=("Segoe UI", 14),
            text_color=TEXT_SECONDARY
        ).pack(pady=(0, 30))

        self.unlock_password_entry = self.create_input(
            container,
            "Master Password",
            show="•",
            width=310
        )
        self.unlock_password_entry.pack(pady=8)
        self.unlock_password_entry.bind("<Return>", lambda event: self.unlock_vault())

        ctk.CTkButton(
            container,
            text="Unlock",
            width=310,
            height=46,
            corner_radius=14,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=("Segoe UI", 14, "bold"),
            command=self.unlock_vault
        ).pack(pady=(28, 45))

    def unlock_vault(self):
        password = self.unlock_password_entry.get().strip()

        if database.verify_master_password(password):
            self.crypto = database.create_crypto(password)
            self.create_app_layout()
        else:
            messagebox.showerror("Access Denied", "Incorrect master password.")

    def create_app_layout(self):
        self.clear_window()
        self.configure(fg_color=APP_BG)

        self.sidebar = ctk.CTkFrame(
            self,
            width=250,
            corner_radius=0,
            fg_color=SIDEBAR_BG
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="SecurePass",
            font=("Segoe UI", 27, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=26, pady=(32, 4))

        ctk.CTkLabel(
            self.sidebar,
            text="Password Manager",
            font=("Segoe UI", 13),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=26, pady=(0, 34))

        self.vault_button = self.create_sidebar_button("Vault", self.show_vault)
        self.vault_button.pack(fill="x", padx=18, pady=6)

        self.generator_button = self.create_sidebar_button("Generator", self.show_generator)
        self.generator_button.pack(fill="x", padx=18, pady=6)

        self.clear_button = self.create_sidebar_button("Clear Form", self.clear_form)
        self.clear_button.pack(fill="x", padx=18, pady=6)

        ctk.CTkLabel(
            self.sidebar,
            text="SQLite • Local Vault",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 12)
        ).pack(side="bottom", pady=26)

        self.main_area = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=APP_BG
        )
        self.main_area.pack(side="right", fill="both", expand=True)

        self.header_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=34, pady=(28, 10))

        self.page_title = ctk.CTkLabel(
            self.header_frame,
            text="Vault",
            font=("Segoe UI", 32, "bold"),
            text_color=TEXT_PRIMARY
        )
        self.page_title.pack(side="left")

        self.search_entry = self.create_input(
            self.header_frame,
            "Search website, username or note...",
            width=330
        )
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_passwords())

        self.create_vault_view()
        self.create_generator_view()

        self.show_vault()
        self.load_passwords()

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
        self.vault_button.configure(
            fg_color=ACCENT if active == "vault" else "transparent",
            hover_color=ACCENT_HOVER if active == "vault" else CARD_SOFT,
            text_color=TEXT_PRIMARY if active == "vault" else TEXT_SECONDARY
        )

        self.generator_button.configure(
            fg_color=ACCENT if active == "generator" else "transparent",
            hover_color=ACCENT_HOVER if active == "generator" else CARD_SOFT,
            text_color=TEXT_PRIMARY if active == "generator" else TEXT_SECONDARY
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
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold"),
            command=command
        )

    def create_vault_view(self):
        self.vault_view = ctk.CTkFrame(self.main_area, fg_color="transparent")

        self.form_frame = ctk.CTkFrame(
            self.vault_view,
            width=360,
            corner_radius=24,
            fg_color=CARD_BG
        )
        self.form_frame.pack(side="left", fill="y", padx=(0, 22))
        self.form_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.form_frame,
            text="Add Password",
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=26, pady=(26, 6))

        ctk.CTkLabel(
            self.form_frame,
            text="Save or update an account",
            font=("Segoe UI", 13),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=26, pady=(0, 22))

        self.website_entry = self.create_input(self.form_frame, "Website")
        self.website_entry.pack(fill="x", padx=26, pady=8)

        self.username_entry = self.create_input(self.form_frame, "Username / Email")
        self.username_entry.pack(fill="x", padx=26, pady=8)

        self.password_entry = self.create_input(self.form_frame, "Password", show="•")
        self.password_entry.pack(fill="x", padx=26, pady=8)
        self.password_entry.bind("<KeyRelease>", lambda event: self.update_strength())

        self.strength_label = ctk.CTkLabel(
            self.form_frame,
            text="Strength: -",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 12)
        )
        self.strength_label.pack(anchor="w", padx=26, pady=(4, 4))

        self.strength_bar = ctk.CTkProgressBar(
            self.form_frame,
            height=8,
            progress_color=ACCENT
        )
        self.strength_bar.pack(fill="x", padx=26, pady=(0, 10))
        self.strength_bar.set(0)

        self.note_entry = self.create_input(self.form_frame, "Note")
        self.note_entry.pack(fill="x", padx=26, pady=8)

        self.save_button = self.create_primary_button(
            self.form_frame,
            "Save / Update",
            self.save_password
        )
        self.save_button.pack(fill="x", padx=26, pady=(24, 10))

        self.generate_button = ctk.CTkButton(
            self.form_frame,
            text="Quick Generate",
            height=42,
            corner_radius=14,
            fg_color=CARD_SOFT,
            hover_color="#334155",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
            command=self.generate_password_quick
        )
        self.generate_button.pack(fill="x", padx=26, pady=8)

        self.table_frame = ctk.CTkFrame(
            self.vault_view,
            corner_radius=24,
            fg_color=CARD_BG
        )
        self.table_frame.pack(side="right", fill="both", expand=True)

        self.table_header = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.table_header.pack(fill="x", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            self.table_header,
            text="Saved Passwords",
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        self.count_label = ctk.CTkLabel(
            self.table_header,
            text="0 items",
            font=("Segoe UI", 13),
            text_color=TEXT_MUTED
        )
        self.count_label.pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(
            self.table_frame,
            fg_color="transparent",
            scrollbar_button_color=CARD_SOFT,
            scrollbar_button_hover_color="#334155"
        )
        self.list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def create_generator_view(self):
        self.generator_view = ctk.CTkFrame(self.main_area, fg_color="transparent")

        card = ctk.CTkFrame(
            self.generator_view,
            corner_radius=24,
            fg_color=CARD_BG
        )
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            card,
            text="Password Generator",
            font=("Segoe UI", 30, "bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", padx=34, pady=(34, 8))

        ctk.CTkLabel(
            card,
            text="Generate strong passwords and send them directly to your vault form.",
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 14)
        ).pack(anchor="w", padx=34, pady=(0, 28))

        self.generated_password_entry = self.create_input(
            card,
            "Generated password will appear here"
        )
        self.generated_password_entry.configure(font=("Segoe UI", 18))
        self.generated_password_entry.pack(fill="x", padx=34, pady=(0, 26))

        self.length_label = ctk.CTkLabel(
            card,
            text="Length: 16",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_PRIMARY
        )
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

        for text, var in [
            ("Uppercase letters", self.uppercase_var),
            ("Numbers", self.digits_var),
            ("Symbols", self.symbols_var)
        ]:
            ctk.CTkCheckBox(
                options,
                text=text,
                variable=var,
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                text_color=TEXT_SECONDARY
            ).pack(anchor="w", pady=7)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=34, pady=16)

        self.create_primary_button(
            btns,
            "Generate",
            self.generate_password_for_generator_page
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            btns,
            text="Use in Vault Form",
            height=46,
            corner_radius=14,
            fg_color=CARD_SOFT,
            hover_color="#334155",
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold"),
            command=self.use_generated_password
        ).pack(side="left")

    def show_vault(self):
        if hasattr(self, "generator_view"):
            self.generator_view.pack_forget()

        if hasattr(self, "vault_view"):
            self.vault_view.pack_forget()
            self.vault_view.pack(fill="both", expand=True, padx=34, pady=22)

        self.page_title.configure(text="Vault")

        if not self.search_entry.winfo_ismapped():
            self.search_entry.pack(side="right")

        self.set_active_nav("vault")

    def show_generator(self):
        if hasattr(self, "vault_view"):
            self.vault_view.pack_forget()

        if hasattr(self, "generator_view"):
            self.generator_view.pack_forget()
            self.generator_view.pack(fill="both", expand=True, padx=34, pady=22)

        self.page_title.configure(text="Generator")
        self.search_entry.pack_forget()
        self.set_active_nav("generator")

    def save_password(self):
        website = self.website_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        note = self.note_entry.get().strip()
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not website or not username or not password:
            messagebox.showerror("Missing Information", "Website, username and password are required.")
            return

        database.add_or_update_password(
            website,
            username,
            password,
            note,
            updated_at,
            self.crypto
        )

        self.clear_form()
        self.load_passwords()

        messagebox.showinfo("Saved", "Password saved or updated successfully.")

    def load_passwords(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        search_text = self.search_entry.get().strip()
        passwords = database.get_passwords(search_text, self.crypto)

        self.count_label.configure(text=f"{len(passwords)} items")

        if not passwords:
            ctk.CTkLabel(
                self.list_frame,
                text="No passwords found.",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 14)
            ).pack(pady=36)
            return

        for item in passwords:
            self.create_password_card(item)

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
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=username,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 13),
            anchor="w"
        ).pack(anchor="w", pady=(6, 0))

        password_label = ctk.CTkLabel(
            left,
            text="•" * len(password),
            text_color=TEXT_MUTED,
            font=("Segoe UI", 13),
            anchor="w"
        )
        password_label.pack(anchor="w", pady=(6, 0))

        if note:
            ctk.CTkLabel(
                left,
                text=note,
                text_color=TEXT_MUTED,
                font=("Segoe UI", 12),
                anchor="w"
            ).pack(anchor="w", pady=(6, 0))

        if updated_at:
            ctk.CTkLabel(
                left,
                text=f"Updated {updated_at}",
                text_color=TEXT_MUTED,
                font=("Segoe UI", 12),
                anchor="w"
            ).pack(anchor="w", pady=(6, 0))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=18, pady=12)

        show_button = ctk.CTkButton(
            right,
            text="Show",
            width=76,
            height=32,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            text_color=TEXT_PRIMARY
        )
        show_button.configure(
            command=lambda: self.toggle_password(password_label, password, show_button)
        )
        show_button.pack(pady=4)

        ctk.CTkButton(
            right,
            text="Copy",
            width=76,
            height=32,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
            command=lambda: self.copy_password(password)
        ).pack(pady=4)

        ctk.CTkButton(
            right,
            text="Delete",
            width=76,
            height=32,
            corner_radius=10,
            fg_color="transparent",
            hover_color=DANGER_HOVER,
            text_color="#fca5a5",
            command=lambda: self.delete_password(password_id)
        ).pack(pady=4)

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
        messagebox.showinfo("Copied", "Password copied to clipboard.")

    def delete_password(self, password_id):
        if not messagebox.askyesno("Delete", "Are you sure you want to delete this password?"):
            return

        database.delete_password(password_id)
        self.load_passwords()

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


if __name__ == "__main__":
    app = SecurePassApp()
    app.mainloop()