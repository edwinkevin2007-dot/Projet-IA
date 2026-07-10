import math
import sqlite3
import numpy as np
from sklearn.tree import DecisionTreeRegressor

DB_NAME = "agri_market.db"

X_train = np.array([
    [2.0,  1, 4.9],
    [5.0,  1, 4.5],
    [15.0, 1, 4.0],
    [30.0, 1, 3.5],
    [60.0, 1, 4.2],
    [10.0, 0, 4.7]  
])

y_train = np.array([99, 92, 75, 50, 30, 0])

ai_model = DecisionTreeRegressor(random_state=42)
ai_model.fit(X_train, y_train)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en kilomètres entre deux points géographiques."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_ranked_providers(harvest_id):
    """Récupère les prestataires et utilise l'IA pour prédire leur score."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT h.id as harvest_id, u.latitude, u.longitude 
        FROM harvests h
        JOIN users u ON h.producer_id = u.id
        WHERE h.id = ?
    ''', (harvest_id,))
    harvest = cursor.fetchone()

    if not harvest:
        conn.close()
        return []

    prod_lat = harvest['latitude']
    prod_lon = harvest['longitude']

    cursor.execute("SELECT id, name, role, latitude, longitude, availability FROM users WHERE role != 'producer'")
    providers = cursor.fetchall()

    ranked_list = []
    for prov in providers:
        distance = haversine_distance(prod_lat, prod_lon, prov['latitude'], prov['longitude'])
        
        
        rating = 4.5 
        
        features = np.array([[distance, prov['availability'], rating]])
        predicted_score = ai_model.predict(features)[0]
        base_price = round(distance * 1500, 2)

        ranked_list.append({
            "id": prov['id'],
            "name": prov['name'],
            "role": prov['role'],
            "distance": round(distance, 2),
            "price_estimate": base_price,
            "score": round(predicted_score, 2)
        })

    conn.close()
    return sorted(ranked_list, key=lambda x: x['score'], reverse=True)