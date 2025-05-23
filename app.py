from flask import Flask, render_template, jsonify, request
import pandas as pd
import random
import json
from typing import Dict, List, Tuple, Optional, Union

app = Flask(__name__)

def load_data() -> Tuple[Dict[str, List[str]], List[str], List[str], Dict[str, List[str]]]:
    """Load weapons, tools, consumables, and ammo types from files."""
    df = pd.read_excel('data/Randomizer_Item_List.xlsx', sheet_name='Sheet1')
    
    weapons = {
        'Large': df['Weapons_Large'].dropna().tolist(),
        'Medium': df['Weapons_Medium'].dropna().tolist(),
        'Small': df['Weapons_Small'].dropna().tolist()
    }
    
    # Add dual pistol variants to Medium weapons
    pistols = [w for w in weapons['Small'] if "Pistol" in w]
    for pistol in pistols:
        weapons['Medium'].append(f"{pistol} x2")
    
    tools = df['Tools'].dropna().unique().tolist()
    consumables = df['Consumables'].dropna().tolist()
    
    with open('data/ammo_types.json', 'r') as f:
        ammo_data = json.load(f)
        weapon_ammo_types = ammo_data['weapon_ammo_types']
    
    return weapons, tools, consumables, weapon_ammo_types

WEAPONS, TOOLS, CONSUMABLES, AMMO_TYPES = load_data()

def is_pistol(weapon_name: str) -> bool:
    """Check if weapon is a pistol (contains 'Pistol' in name)."""
    return "Pistol" in weapon_name

def randomize_weapons(
    quartermaster: bool,
    allow_duplicates: bool,
    allow_special_ammo: bool,
    max_attempts: int = 100
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Randomize weapons with all constraints."""
    weapons = WEAPONS.copy()
    
    for _ in range(max_attempts):
        primary_type = random.choice(['Large', 'Medium', 'Small'])
        primary = random.choice(weapons[primary_type])
        
        if quartermaster:
            if primary_type == 'Large':
                secondary_options = weapons['Medium'] + weapons['Small']
            elif primary_type == 'Medium':
                secondary_options = weapons['Large'] + weapons['Medium'] + weapons['Small']
            else:
                secondary_options = weapons['Small']
        else:
            if primary_type == 'Large':
                secondary_options = weapons['Small']
            elif primary_type == 'Medium':
                secondary_options = weapons['Medium'] + weapons['Small']
            else:
                secondary_options = weapons['Small']
        
        if not allow_duplicates:
            # Remove exact matches and dual variants of the same pistol
            base_primary = primary.replace(' x2', '')
            secondary_options = [
                w for w in secondary_options 
                if w != primary and w.replace(' x2', '') != base_primary
            ]
            if not secondary_options:
                continue
        
        secondary = random.choice(secondary_options)
        secondary_type = next(size for size in weapons if secondary in weapons[size])
        
        # Check if secondary is a dual pistol variant
        is_dual = secondary.endswith(' x2') and secondary_type == 'Medium'
        
        # Get ammo types
        ammo = {
            primary: random.choice(
                ['Standard'] if not allow_special_ammo else
                AMMO_TYPES.get(primary.replace(' x2', ''), ['Standard'])
            ),
            secondary: random.choice(
                ['Standard'] if not allow_special_ammo else
                AMMO_TYPES.get(secondary.replace(' x2', ''), ['Standard'])
            )
        }
        
        return {
            'primary': {
                'name': primary,
                'type': primary_type,
                'is_dual': False  # Primary is never dual
            },
            'secondary': {
                'name': secondary,
                'type': secondary_type,
                'is_dual': is_dual
            },
            'ammo': ammo
        }
    
    # Fallback if no valid combination found
    fallback_weapon = random.choice(weapons['Medium'])
    return {
        'primary': {
            'name': fallback_weapon,
            'type': 'Medium',
            'is_dual': False
        },
        'secondary': {
            'name': fallback_weapon,
            'type': 'Medium',
            'is_dual': False
        },
        'ammo': {
            fallback_weapon: 'Standard'
        }
    }

def randomize_ammo(weapons: List[str], allow_special_ammo: bool) -> Dict[str, str]:
    """Randomize ammo types for weapons."""
    return {
        weapon: random.choice(
            ['Standard'] if not allow_special_ammo else
            AMMO_TYPES.get(weapon.replace(' x2', ''), ['Standard'])
        )
        for weapon in weapons
    }

def randomize_tools(force_first_aid: bool) -> List[str]:
    """Randomize tools with no duplicates."""
    tools = TOOLS.copy()
    if force_first_aid and 'First Aid Kit' in tools:
        tools.remove('First Aid Kit')
        return ['First Aid Kit'] + random.sample(tools, 3)
    return random.sample(tools, 4)

def randomize_traits(max_points: int = 10) -> Dict[str, Union[List[str], int]]:
    """Randomize traits within given point budget."""
    traits_df = pd.read_excel('data/Hunt_Traits.xlsx', sheet_name='Sheet1')
    traits = traits_df.to_dict('records')
    random.shuffle(traits)
    
    selected_traits = []
    remaining_points = max_points
    total_spent = 0
    
    for trait in traits:
        if trait['Cost'] <= remaining_points:
            selected_traits.append(trait['Trait'])
            remaining_points -= trait['Cost']
            total_spent += trait['Cost']
            if remaining_points <= 0:
                break
    
    return {
        'traits': selected_traits,
        'points_used': total_spent,
        'points_remaining': remaining_points
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/randomize', methods=['POST'])
def api_randomize():
    data = request.json
    quartermaster = data.get('quartermaster', False)
    allow_duplicates = data.get('allow_duplicates', False)
    allow_special_ammo = data.get('allow_special_ammo', False)
    force_first_aid = data.get('force_first_aid', False)
    trait_points = data.get('trait_points', 10)
    
    weapons_data = randomize_weapons(
        quartermaster, allow_duplicates, allow_special_ammo
    )
    
    return jsonify({
        'primary_weapon': weapons_data['primary']['name'],
        'secondary_weapon': weapons_data['secondary']['name'],
        'primary_type': weapons_data['primary']['type'],
        'secondary_type': weapons_data['secondary']['type'],
        'is_dual': weapons_data['secondary']['is_dual'],
        'ammo': weapons_data['ammo'],
        'tools': randomize_tools(force_first_aid),
        'consumables': [random.choice(CONSUMABLES) for _ in range(4)],
        'traits': randomize_traits(trait_points)
    })

@app.route('/api/randomize-weapons', methods=['POST'])
def api_randomize_weapons():
    data = request.json
    return jsonify(randomize_weapons(
        data.get('quartermaster', False),
        data.get('allow_duplicates', False),
        data.get('allow_special_ammo', False)
    ))

@app.route('/api/randomize-tools', methods=['POST'])
def api_randomize_tools():
    data = request.json
    return jsonify({
        'tools': randomize_tools(data.get('force_first_aid', False))
    })

@app.route('/api/randomize-consumables', methods=['POST'])
def api_randomize_consumables():
    return jsonify({
        'consumables': [random.choice(CONSUMABLES) for _ in range(4)]
    })

@app.route('/api/randomize-traits', methods=['POST'])
def api_randomize_traits():
    data = request.json
    return jsonify(randomize_traits(data.get('trait_points', 10)))

@app.route('/api/get-all-weapons', methods=['GET'])
def get_all_weapons():
    return jsonify(WEAPONS)

@app.route('/api/get-all-tools', methods=['GET'])
def get_all_tools():
    return jsonify({'tools': TOOLS})

@app.route('/api/get-all-consumables', methods=['GET'])
def get_all_consumables():
    return jsonify({'consumables': CONSUMABLES})

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
if __name__ == '__main__':
    app.run(debug=True)