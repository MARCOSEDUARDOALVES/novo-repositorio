import pandas as pd
import json

# Carregar dados preparados
df_prepared = pd.read_csv('prepared_ml_data.csv')
feature_names = df_prepared.drop(columns=['name', 'occupation', 'occupation_encoded']).columns.tolist()

print(f"Total de features esperadas: {len(feature_names)}")
print("\nPrimeiras 20 features:")
for i, feat in enumerate(feature_names[:20]):
    print(f"{i+1}. {feat}")

print("\nÚltimas 20 features:")
for i, feat in enumerate(feature_names[-20:]):
    print(f"{len(feature_names)-19+i}. {feat}")

# Verificar quais colunas são categóricas
categorical_cols = [col for col in df_prepared.columns if 'sign' in col or 'element' in col or 'modality' in col]
print(f"\nTotal de colunas categóricas originais: {len(categorical_cols)}")
print("Colunas categóricas:")
for col in categorical_cols:
    print(f"  - {col}")

# Verificar quais colunas são numéricas
numeric_cols = [col for col in df_prepared.columns if 'house' in col]
print(f"\nTotal de colunas numéricas (casas): {len(numeric_cols)}")
print("Colunas numéricas:")
for col in numeric_cols:
    print(f"  - {col}")

