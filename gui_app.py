import tkinter as tk
from tkinter import ttk, messagebox
import tkintermapview
import sqlite3
from database import DB_NAME, init_db
from scoring import get_ranked_providers

class AgriMarketDesktop:
    def __init__(self, root):
        self.root = root
        self.root.title("AgriMarketFlow - Madagascar Desktop")
        self.root.geometry("1100x650")
        self.root.configure(bg="#f4f7f6")
        
        
        init_db()
        
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", background="#27ae60", foreground="white", font=("Helvetica", 10, "bold"))
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#ecf0f1")

        
        left_panel = tk.Frame(root, bg="white", padx=15, pady=15, bd=1, relief="solid")
        left_panel.place(x=20, y=20, width=450, height=610)
        
        tk.Label(left_panel, text="AgriMarketFlow (Desktop)", font=("Helvetica", 16, "bold"), bg="white", fg="#2c3e50").pack(anchor="w", pady=5)
        
        
        lbl_frame = tk.LabelFrame(left_panel, text=" 1. Publier une récolte ", bg="white", font=("Helvetica", 10, "bold"))
        lbl_frame.pack(fill="x", pady=10)
        
        tk.Label(lbl_frame, text="Produit Agricole :", bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ent_product = tk.Entry(lbl_frame, width=25)
        self.ent_product.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(lbl_frame, text="Quantité (kg) :", bg="white").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ent_qty = tk.Entry(lbl_frame, width=25)
        self.ent_qty.grid(row=1, column=1, padx=5, pady=5)
        
        btn_add = ttk.Button(lbl_frame, text="Publier", command=self.add_harvest)
        btn_add.grid(row=2, column=0, columnspan=2, pady=10)

        
        tk.Label(left_panel, text="Récoltes Actuelles :", font=("Helvetica", 11, "bold"), bg="white").pack(anchor="w", pady=5)
        
        self.tree_harvests = ttk.Treeview(left_panel, columns=("ID", "Produit", "Quantité"), show="headings", height=8)
        self.tree_harvests.heading("ID", text="ID")
        self.tree_harvests.heading("Produit", text="Produit")
        self.tree_harvests.heading("Quantité", text="Quantité (kg)")
        self.tree_harvests.column("ID", width=40, anchor="center")
        self.tree_harvests.pack(fill="x", pady=5)
        
        btn_match = ttk.Button(left_panel, text="Trouver Prestataires", command=self.match_ai)
        btn_match.pack(fill="x", pady=10)

        
        right_panel = tk.Frame(root, bg="#f4f7f6")
        right_panel.place(x=490, y=20, width=590, height=610)
        
        
        tk.Label(right_panel, text="📋 Suggestions :", font=("Helvetica", 11, "bold"), bg="#f4f7f6").pack(anchor="w")
        self.tree_matches = ttk.Treeview(right_panel, columns=("Nom", "Rôle", "Distance", "Score"), show="headings", height=5)
        self.tree_matches.heading("Nom", text="Nom")
        self.tree_matches.heading("Rôle", text="Rôle")
        self.tree_matches.heading("Distance", text="Distance")
        self.tree_matches.heading("Score", text="Score IA")
        self.tree_matches.pack(fill="x", pady=5)

        
        self.map_widget = tkintermapview.TkinterMapView(right_panel, corner_radius=10)
        self.map_widget.pack(fill="both", expand=True, pady=10)
        # Centrer sur Madagascar (Antananarivo)
        self.map_widget.set_position(-18.8792, 47.5079)
        self.map_widget.set_zoom(6)
        
        self.load_harvests()

    def load_harvests(self):
        """Charge les récoltes depuis la BDD SQLite."""
        for item in self.tree_harvests.get_children():
            self.tree_harvests.delete(item)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_name, quantity FROM harvests WHERE status='available'")
        for row in cursor.fetchall():
            self.tree_harvests.insert("", "end", values=row)
        conn.close()

    def add_harvest(self):
        """Ajoute une récolte liée par défaut au premier producteur disponible."""
        product = self.ent_product.get()
        qty = self.ent_qty.get()
        
        if not product or not qty:
            messagebox.showwarning("Erreur", "Veuillez remplir tous les champs.")
            return
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE role='producer' LIMIT 1")
        prod = cursor.fetchone()
        prod_id = prod[0] if prod else 1 # Fallback ID 1
        
        cursor.execute("INSERT INTO harvests (producer_id, product_name, quantity) VALUES (?, ?, ?)", (prod_id, product, qty))
        conn.commit()
        conn.close()
        
        self.ent_product.delete(0, tk.END)
        self.ent_qty.delete(0, tk.END)
        self.load_harvests()
        messagebox.showinfo("Succès", "Récolte publiée avec succès !")

    def match_ai(self):
        """Applique le modèle de scoring IA et affiche les résultats sur l'interface et la carte."""
        selected = self.tree_harvests.selection()
        if not selected:
            messagebox.showwarning("Sélection", "Veuillez sélectionner une récolte dans le tableau.")
            return
            
        harvest_id = self.tree_harvests.item(selected[0])['values'][0]
        
        
        providers = get_ranked_providers(harvest_id)
        
        
        for item in self.tree_matches.get_children():
            self.tree_matches.delete(item)
        self.map_widget.delete_all_marker()
        
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT u.name, u.latitude, u.longitude FROM harvests h JOIN users u ON h.producer_id = u.id WHERE h.id=?", (harvest_id,))
        h_info = cursor.fetchone()
        
        if h_info:
            
            self.map_widget.set_marker(h_info[1], h_info[2], text=h_info[0], marker_color_circle="green")
            self.map_widget.set_position(h_info[1], h_info[2])
            
            
        for p in providers:
            self.tree_matches.insert("", "end", values=(p['name'], p['role'], f"{p['distance']} km", f"{p['score']} pts"))
            
            
            cursor.execute("SELECT latitude, longitude FROM users WHERE id=?", (p['id'],))
            pos = cursor.fetchone()
            if pos:
                color = "orange" if p['role'] == 'collector' else "blue"
                self.map_widget.set_marker(pos[0], pos[1], text=f"{p['name']} ({p['score']} pts)", marker_color_circle=color)
                
        conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = AgriMarketDesktop(root)
    root.mainloop()