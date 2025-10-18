import os

# Configurar o caminho das efemérides ANTES de importar qualquer biblioteca que use swisseph
EPHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ephe'))
os.environ['SE_EPHE_PATH'] = EPHE_PATH

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import joblib
import pandas as pd
import numpy as np
from immanuel import charts
import swisseph as swe

astro_bp = Blueprint('astro', __name__)

# Configurar o caminho das efemérides do Swiss Ephemeris
swe.set_ephe_path(EPHE_PATH)
print(f"Caminho das efemérides configurado: {EPHE_PATH}")

# Carregar o modelo e os dados necessários
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'random_forest_model.pkl')
OCCUPATION_MAPPING_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'occupation_label_mapping.json')
PREPARED_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'prepared_ml_data.csv')

# Carregar modelo e mapeamento
model = joblib.load(MODEL_PATH)
with open(OCCUPATION_MAPPING_PATH, 'r') as f:
    occupation_labels = json.load(f)

# Carregar dados preparados para obter nomes das features
df_prepared = pd.read_csv(PREPARED_DATA_PATH)
feature_names = df_prepared.drop(columns=['name', 'occupation', 'occupation_encoded']).columns.tolist()

def get_astrological_features(birth_date, birth_time, latitude, longitude):
    """
    Gera características astrológicas para uma data, hora e local de nascimento.
    """
    try:
        birth_datetime_str = f"{birth_date} {birth_time}"
        birth_datetime = datetime.strptime(birth_datetime_str, '%Y-%m-%d %H:%M:%S')
        
        native = charts.Subject(
            date_time=birth_datetime,
            latitude=latitude,
            longitude=longitude,
        )

        natal = charts.Natal(native)
        
        features = {}
        celestial_objects = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

        natal_chart = {}
        
        for obj_name_expected in celestial_objects:
            obj_prefix = obj_name_expected.lower()
            found_obj = None
            
            # Tentar acessar via getattr primeiro
            found_obj = getattr(natal, obj_name_expected.lower(), None)
            
            # Se não encontrado, procurar em natal.objects
            if not found_obj:
                for obj_id, obj_data in natal.objects.items():
                    if hasattr(obj_data, 'name') and obj_data.name == obj_name_expected:
                        found_obj = obj_data
                        break
            
            if found_obj:
                sign = found_obj.sign.name if hasattr(found_obj, 'sign') and found_obj.sign else 'Unknown'
                house = found_obj.house.number if hasattr(found_obj, 'house') and found_obj.house else 0
                element = found_obj.sign.element if hasattr(found_obj, 'sign') and found_obj.sign and hasattr(found_obj.sign, 'element') else 'Unknown'
                modality = found_obj.sign.modality if hasattr(found_obj, 'sign') and found_obj.sign and hasattr(found_obj.sign, 'modality') else 'Unknown'
                
                features[f'{obj_prefix}_sign'] = sign
                features[f'{obj_prefix}_house'] = house
                features[f'{obj_prefix}_element'] = element
                features[f'{obj_prefix}_modality'] = modality
                
                natal_chart[obj_name_expected] = {
                    'sign': sign,
                    'house': house,
                    'element': element,
                    'modality': modality
                }
            else:
                features[f'{obj_prefix}_sign'] = 'Unknown'
                features[f'{obj_prefix}_house'] = 0
                features[f'{obj_prefix}_element'] = 'Unknown'
                features[f'{obj_prefix}_modality'] = 'Unknown'
                
                natal_chart[obj_name_expected] = {
                    'sign': 'Unknown',
                    'house': 0,
                    'element': 'Unknown',
                    'modality': 'Unknown'
                }

        # Ascendente e Meio do Céu
        ascendant_obj = getattr(natal, 'ascendant', None)
        if ascendant_obj:
            features['ascendant_sign'] = ascendant_obj.sign.name if hasattr(ascendant_obj, 'sign') and ascendant_obj.sign else 'Unknown'
            features['ascendant_house'] = ascendant_obj.house.number if hasattr(ascendant_obj, 'house') and ascendant_obj.house else 0
            natal_chart['Ascendant'] = {
                'sign': features['ascendant_sign'],
                'house': features['ascendant_house']
            }
        else:
            features['ascendant_sign'] = 'Unknown'
            features['ascendant_house'] = 0
            natal_chart['Ascendant'] = {'sign': 'Unknown', 'house': 0}

        mc_obj = getattr(natal, 'mc', None)
        if mc_obj:
            features['mc_sign'] = mc_obj.sign.name if hasattr(mc_obj, 'sign') and mc_obj.sign else 'Unknown'
            features['mc_house'] = mc_obj.house.number if hasattr(mc_obj, 'house') and mc_obj.house else 0
            natal_chart['MC'] = {
                'sign': features['mc_sign'],
                'house': features['mc_house']
            }
        else:
            features['mc_sign'] = 'Unknown'
            features['mc_house'] = 0
            natal_chart['MC'] = {'sign': 'Unknown', 'house': 0}

        return features, natal_chart
    except Exception as e:
        raise Exception(f"Erro ao gerar características astrológicas: {str(e)}")

def prepare_features_for_model(features):
    """
    Transforma as características astrológicas no formato esperado pelo modelo.
    Cria as mesmas colunas one-hot que existem no conjunto de treino.
    """
    # Inicializar DataFrame com zeros para todas as features esperadas
    result_df = pd.DataFrame(0, index=[0], columns=feature_names)
    
    # Preencher as casas (features numéricas)
    planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
    for planet in planets:
        house_col = f"{planet}_house"
        if house_col in result_df.columns:
            result_df[house_col] = features.get(house_col, 0)
    
    # Preencher ascendente e MC
    result_df['ascendant_house'] = features.get('ascendant_house', 0)
    result_df['mc_house'] = features.get('mc_house', 0)
    
    # Preencher as features categóricas (one-hot encoded)
    for planet in planets:
        # Sign
        sign = features.get(f"{planet}_sign", "Unknown")
        sign_col = f"{planet}_sign_{sign}"
        if sign_col in result_df.columns:
            result_df[sign_col] = 1
        
        # Element
        element = features.get(f"{planet}_element", "Unknown")
        element_col = f"{planet}_element_{element}"
        if element_col in result_df.columns:
            result_df[element_col] = 1
        
        # Modality
        modality = features.get(f"{planet}_modality", "Unknown")
        modality_col = f"{planet}_modality_{modality}"
        if modality_col in result_df.columns:
            result_df[modality_col] = 1
    
    # Preencher ascendant_sign e mc_sign (apenas Unknown está presente no treino)
    ascendant_sign = features.get('ascendant_sign', 'Unknown')
    if f'ascendant_sign_{ascendant_sign}' in result_df.columns:
        result_df[f'ascendant_sign_{ascendant_sign}'] = 1
    
    mc_sign = features.get('mc_sign', 'Unknown')
    if f'mc_sign_{mc_sign}' in result_df.columns:
        result_df[f'mc_sign_{mc_sign}'] = 1
    
    return result_df

@astro_bp.route('/health', methods=['GET'])
def health():
    """Endpoint de verificação de saúde da API."""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })

@astro_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Endpoint principal para análise astrológica.
    Recebe dados de nascimento e retorna previsões de profissões.
    """
    try:
        data = request.json
        
        # Validar dados de entrada
        required_fields = ['birth_date', 'birth_time', 'latitude', 'longitude']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obrigatório ausente: {field}'}), 400
        
        name = data.get('name', 'Usuário')
        birth_date = data['birth_date']
        birth_time = data['birth_time']
        latitude = float(data["latitude"]) if data["latitude"] else 0.0
        longitude = float(data["longitude"]) if data["longitude"] else 0.0
        
        # Gerar características astrológicas
        features, natal_chart = get_astrological_features(birth_date, birth_time, latitude, longitude)
        
        # Preparar features para o modelo
        X = prepare_features_for_model(features)
        
        # Fazer previsão
        probabilities = model.predict_proba(X)[0]
        
        # Obter as top 5 profissões mais prováveis
        top_indices = np.argsort(probabilities)[::-1][:5]
        predictions = []
        
        for idx in top_indices:
            profession = occupation_labels[idx]
            probability = float(probabilities[idx])
            
            # Determinar nível de confiança
            if probability > 0.5:
                confidence = 'high'
            elif probability > 0.2:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            predictions.append({
                'profession': profession,
                'probability': round(probability, 4),
                'confidence': confidence
            })
        
        # Gerar interpretação
        interpretation = generate_interpretation(natal_chart, predictions, features)
        
        # Calcular características mais influentes
        feature_importance = get_top_features(X, features)
        
        # Encontrar perfis similares
        similar_profiles = find_similar_profiles(X)
        
        return jsonify({
            'natal_chart': natal_chart,
            'predictions': predictions,
            'interpretation': interpretation,
            'feature_importance': feature_importance,
            'similar_profiles': similar_profiles
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_interpretation(natal_chart, predictions, features):
    """
    Gera uma interpretação textual baseada nas características astrológicas.
    """
    top_profession = predictions[0]['profession'] if predictions else 'Desconhecida'
    
    summary = f"Baseado nas características astrológicas do seu mapa natal, a profissão mais provável é {top_profession}. "
    
    key_factors = []
    
    # Analisar Sol
    sun = natal_chart.get('Sun', {})
    if sun.get('sign') != 'Unknown':
        key_factors.append(f"Sol em {sun['sign']} na Casa {sun['house']}: Indica sua essência e propósito de vida.")
    
    # Analisar Lua
    moon = natal_chart.get('Moon', {})
    if moon.get('sign') != 'Unknown':
        key_factors.append(f"Lua em {moon['sign']} na Casa {moon['house']}: Representa suas emoções e necessidades internas.")
    
    # Analisar Meio do Céu (MC)
    mc = natal_chart.get('MC', {})
    if mc.get('sign') != 'Unknown':
        key_factors.append(f"Meio do Céu em {mc['sign']}: Relacionado à sua carreira e imagem pública.")
    
    return {
        'summary': summary,
        'key_factors': key_factors
    }

def get_top_features(X, features):
    """
    Retorna as características mais influentes para a predição.
    """
    feature_importances = model.feature_importances_
    
    # Obter os índices das top 10 features mais importantes
    top_indices = np.argsort(feature_importances)[::-1][:10]
    
    most_influential = []
    for idx in top_indices:
        feature_name = feature_names[idx]
        feature_value = X.iloc[0, idx]
        importance = float(feature_importances[idx])
        
        most_influential.append({
            'feature': feature_name,
            'value': float(feature_value),
            'importance': round(importance, 4)
        })
    
    return {'most_influential': most_influential}

def find_similar_profiles(X):
    """
    Encontra perfis similares no conjunto de dados treinado.
    """
    # Carregar dados preparados
    df_train = pd.read_csv(PREPARED_DATA_PATH)
    X_train = df_train.drop(columns=['name', 'occupation', 'occupation_encoded'])
    
    # Calcular distância euclidiana
    from scipy.spatial.distance import cdist
    distances = cdist(X, X_train, metric='euclidean')[0]
    
    # Obter os 5 perfis mais similares
    top_indices = np.argsort(distances)[:5]
    
    similar_profiles = []
    for idx in top_indices:
        name = df_train.iloc[idx]['name']
        profession = df_train.iloc[idx]['occupation']
        similarity = 1 / (1 + distances[idx])  # Converter distância em similaridade
        
        similar_profiles.append({
            'name': name,
            'profession': profession,
            'similarity': round(float(similarity), 4)
        })
    
    return similar_profiles

