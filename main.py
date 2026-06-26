import customtkinter as ctk
from tkinter import messagebox
import random
import string
from datetime import datetime
import database

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SecurePassApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        database.create_table()

        self.title("SecurePass Manager")
        self.geometry("1100x680")
        self.minsize(1000, 620)

        self.create_layout()
        self.load_passwords()
        self.show_vault()

    def create_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="SecurePass",
            font=("Segoe UI", 26, "bold")
        ).pack(pady=(30, 5))

        ctk.CTkLabel(
            self.sidebar,
            text="Password Manager",
            text_color="#9ca3af"
        ).pack(pady=(0, 30))

        self.vault_button = ctk.CTkButton(
            self.sidebar,
            text="Vault",
            height=42,
            command=self.show_vault
        )
        self.vault_button.pack(fill="x", padx=20, pady=8)

        self.generator_button = ctk.CTkButton(
            self.sidebar,
            text="Generator",
            height=42,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.show_generator
        )
        self.generator_button.pack(fill="x", padx=20, pady=8)

        self.clear_button = ctk.CTkButton(
            self.sidebar,
            text="Clear Form",
            height=42,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.clear_form
        )
        self.clear_button.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            self.sidebar,
            text="SQLite version",
            text_color="#6b7280"
        ).pack(side="bottom", pady=25)

        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#111827")
        self.main_area.pack(side="right", fill="both", expand=True)

        self.header_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=30, pady=(25, 10))

        self.page_title = ctk.CTkLabel(
            self.header_frame,
            text="Vault",
            font=("Segoe UI", 30, "bold")
        )
        self.page_title.pack(side="left")

        self.search_entry = ctk.CTkEntry(
            self.header_frame,
            placeholder_text="Search website or username...",
            width=320,
            height=38
        )
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_passwords())

        self.create_vault_view()
        self.create_generator_view()

    def create_vault_view(self):
        self.vault_view = ctk.CTkFrame(self.main_area, fg_color="transparent")

        self.form_frame = ctk.CTkFrame(self.vault_view, width=340, corner_radius=18)
        self.form_frame.pack(side="left", fill="y", padx=(0, 20))
        self.form_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.form_frame,
            text="Add Password",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w", padx=25, pady=(25, 18))

        self.website_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Website",
            height=42
        )
        self.website_entry.pack(fill="x", padx=25, pady=8)

        self.username_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Username / Email",
            height=42
        )
        self.username_entry.pack(fill="x", padx=25, pady=8)

        self.password_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Password",
            show="•",
            height=42
        )
        self.password_entry.pack(fill="x", padx=25, pady=8)
        self.password_entry.bind("<KeyRelease>", lambda event: self.update_strength())

        self.strength_label = ctk.CTkLabel(
            self.form_frame,
            text="Strength: -",
            text_color="#9ca3af"
        )
        self.strength_label.pack(anchor="w", padx=25, pady=(0, 2))

        self.strength_bar = ctk.CTkProgressBar(self.form_frame)
        self.strength_bar.pack(fill="x", padx=25, pady=(0, 8))
        self.strength_bar.set(0)

        self.note_entry = ctk.CTkEntry(
            self.form_frame,
            placeholder_text="Note",
            height=42
        )
        self.note_entry.pack(fill="x", padx=25, pady=8)

        self.save_button = ctk.CTkButton(
            self.form_frame,
            text="Save / Update Password",
            height=44,
            command=self.save_password
        )
        self.save_button.pack(fill="x", padx=25, pady=(22, 8))

        self.generate_button = ctk.CTkButton(
            self.form_frame,
            text="Quick Generate Password",
            height=40,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.generate_password_quick
        )
        self.generate_button.pack(fill="x", padx=25, pady=8)

        self.table_frame = ctk.CTkFrame(self.vault_view, corner_radius=18)
        self.table_frame.pack(side="right", fill="both", expand=True)

        self.table_header = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.table_header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            self.table_header,
            text="Saved Passwords",
            font=("Segoe UI", 22, "bold")
        ).pack(side="left")

        self.count_label = ctk.CTkLabel(
            self.table_header,
            text="0 items",
            text_color="#9ca3af"
        )
        self.count_label.pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(
            self.table_frame,
            fg_color="transparent"
        )
        self.list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def create_generator_view(self):
        self.generator_view = ctk.CTkFrame(self.main_area, fg_color="transparent")

        card = ctk.CTkFrame(self.generator_view, corner_radius=18)
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            card,
            text="Password Generator",
            font=("Segoe UI", 28, "bold")
        ).pack(anchor="w", padx=30, pady=(30, 10))

        ctk.CTkLabel(
            card,
            text="Generate strong passwords and send them directly to your vault form.",
            text_color="#9ca3af",
            font=("Segoe UI", 14)
        ).pack(anchor="w", padx=30, pady=(0, 25))

        self.generated_password_entry = ctk.CTkEntry(
            card,
            height=50,
            font=("Segoe UI", 18),
            placeholder_text="Generated password will appear here"
        )
        self.generated_password_entry.pack(fill="x", padx=30, pady=(0, 20))

        self.length_label = ctk.CTkLabel(
            card,
            text="Length: 16",
            font=("Segoe UI", 14, "bold")
        )
        self.length_label.pack(anchor="w", padx=30)

        self.length_slider = ctk.CTkSlider(
            card,
            from_=8,
            to=32,
            number_of_steps=24,
            command=self.update_length_label
        )
        self.length_slider.set(16)
        self.length_slider.pack(fill="x", padx=30, pady=(8, 25))

        options = ctk.CTkFrame(card, fg_color="transparent")
        options.pack(fill="x", padx=30, pady=(0, 20))

        self.uppercase_var = ctk.BooleanVar(value=True)
        self.digits_var = ctk.BooleanVar(value=True)
        self.symbols_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            options,
            text="Uppercase letters",
            variable=self.uppercase_var
        ).pack(anchor="w", pady=6)

        ctk.CTkCheckBox(
            options,
            text="Numbers",
            variable=self.digits_var
        ).pack(anchor="w", pady=6)

        ctk.CTkCheckBox(
            options,
            text="Symbols",
            variable=self.symbols_var
        ).pack(anchor="w", pady=6)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=30, pady=20)

        ctk.CTkButton(
            btns,
            text="Generate",
            height=44,
            command=self.generate_password_for_generator_page
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btns,
            text="Use in Vault Form",
            height=44,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.use_generated_password
        ).pack(side="left")

    def show_vault(self):
        self.generator_view.pack_forget()
        self.vault_view.pack(fill="both", expand=True, padx=30, pady=20)
        self.page_title.configure(text="Vault")
        self.search_entry.pack(side="right")

    def show_generator(self):
        self.vault_view.pack_forget()
        self.generator_view.pack(fill="both", expand=True, padx=30, pady=20)
        self.page_title.configure(text="Generator")
        self.search_entry.pack_forget()

    def save_password(self):
        website = self.website_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        note = self.note_entry.get().strip()
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not website or not username or not password:
            messagebox.showerror(
                "Missing Information",
                "Website, username and password are required."
            )
            return

        database.add_or_update_password(
            website,
            username,
            password,
            note,
            updated_at
        )

        self.clear_form()
        self.load_passwords()

        messagebox.showinfo("Saved", "Password saved or updated successfully.")

    def load_passwords(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        search_text = self.search_entry.get().strip()
        passwords = database.get_passwords(search_text)

        self.count_label.configure(text=f"{len(passwords)} items")

        if not passwords:
            ctk.CTkLabel(
                self.list_frame,
                text="No passwords found.",
                text_color="#9ca3af",
                font=("Segoe UI", 14)
            ).pack(pady=30)
            return

        for item in passwords:
            self.create_password_card(item)

    def create_password_card(self, item):
        password_id, website, username, password, note, updated_at = item

        card = ctk.CTkFrame(self.list_frame, corner_radius=14)
        card.pack(fill="x", pady=8, padx=5)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=18, pady=14)

        ctk.CTkLabel(
            left,
            text=website,
            font=("Segoe UI", 17, "bold"),
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=f"Username: {username}",
            text_color="#d1d5db",
            anchor="w"
        ).pack(anchor="w", pady=(3, 0))

        password_label = ctk.CTkLabel(
            left,
            text=f"Password: {'•' * len(password)}",
            text_color="#9ca3af",
            anchor="w"
        )
        password_label.pack(anchor="w", pady=(3, 0))

        if note:
            ctk.CTkLabel(
                left,
                text=f"Note: {note}",
                text_color="#6b7280",
                anchor="w"
            ).pack(anchor="w", pady=(3, 0))

        if updated_at:
            ctk.CTkLabel(
                left,
                text=f"Updated: {updated_at}",
                text_color="#6b7280",
                anchor="w"
            ).pack(anchor="w", pady=(3, 0))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=15)

        show_button = ctk.CTkButton(right, text="Show", width=75)
        show_button.configure(
            command=lambda: self.toggle_password(password_label, password, show_button)
        )
        show_button.pack(pady=4)

        ctk.CTkButton(
            right,
            text="Copy",
            width=75,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=lambda: self.copy_password(password)
        ).pack(pady=4)

        ctk.CTkButton(
            right,
            text="Delete",
            width=75,
            fg_color="#dc2626",
            hover_color="#991b1b",
            command=lambda: self.delete_password(password_id)
        ).pack(pady=4)

    def toggle_password(self, label, password, button):
        if "•" in label.cget("text"):
            label.configure(text=f"Password: {password}")
            button.configure(text="Hide")
        else:
            label.configure(text=f"Password: {'•' * len(password)}")
            button.configure(text="Show")

    def copy_password(self, password):
        self.clipboard_clear()
        self.clipboard_append(password)
        messagebox.showinfo("Copied", "Password copied to clipboard.")

    def delete_password(self, password_id):
        if not messagebox.askyesno(
            "Delete",
            "Are you sure you want to delete this password?"
        ):
            return

        database.delete_password(password_id)
        self.load_passwords()

    def update_strength(self):
        password = self.password_entry.get()
        score = self.calculate_strength(password)

        self.strength_bar.set(score / 5)

        if not password:
            self.strength_label.configure(text="Strength: -", text_color="#9ca3af")
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
            messagebox.showerror(
                "Generator Error",
                "Please select at least one character type."
            )
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
        self.website_entry.delete(0, "end")
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.note_entry.delete(0, "end")

        self.website_entry.configure(placeholder_text="Website")
        self.username_entry.configure(placeholder_text="Username / Email")
        self.password_entry.configure(placeholder_text="Password", show="•")
        self.note_entry.configure(placeholder_text="Note")

        self.strength_bar.set(0)
        self.strength_label.configure(text="Strength: -", text_color="#9ca3af")

        self.focus()


if __name__ == "__main__":
    app = SecurePassApp()
    app.mainloop()