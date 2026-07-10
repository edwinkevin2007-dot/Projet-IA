import sqlite3

DB_NAME = "agri_market.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    #Profils
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL, -- 'producer', 'collector', 'transporter'
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            availability INTEGER DEFAULT 1 -- 1 pour disponible, 0 sinon (utile pour transporteurs)
        )
    ''')
    
    #Récoltes (publiées par producteurs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS harvests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producer_id INTEGER,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            status TEXT DEFAULT 'available', -- 'available', 'in_progress', 'completed'
            FOREIGN KEY(producer_id) REFERENCES users(id)
        )
    ''')
    
    #Offres (collecteurs/transporteurs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            harvest_id INTEGER,
            provider_id INTEGER, -- ID collecteur ou transporteur
            price REAL NOT NULL,
            status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
            FOREIGN KEY(harvest_id) REFERENCES harvests(id),
            FOREIGN KEY(provider_id) REFERENCES users(id)
        )
    ''')
        
    conn.commit()
    conn.close()
    print("Base de données initialisée avec succès !")

if __name__ == "__main__":
    init_db()