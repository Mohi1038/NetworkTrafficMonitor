import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.decomposition import PCA
from sklearn.metrics import classification_report
import joblib

# Step 1: Load data
hist = pd.read_csv("n2_downsampled_filtered_4.csv")
rt = pd.read_csv("realtime_flow_features.csv")

# Step 2: Encode 'protocol' column
protocol_map = {'TCP': 6, 'UDP': 17, 'ICMP': 1}
hist['protocol'] = hist['protocol'].map(protocol_map).fillna(-1).astype(int)
rt['protocol'] = rt['protocol'].map(protocol_map).fillna(-1).astype(int)

# Step 3: Define feature columns (excluding non-numeric only)
exclude_cols = ["src_ip", "dst_ip", "label"]
features = [col for col in hist.columns if col not in exclude_cols]

# Step 4: Apply MinMax Scaling
scaler = MinMaxScaler()
hist_scaled = hist.copy()
hist_scaled[features] = scaler.fit_transform(hist[features])
rt_scaled = rt.copy()
rt_scaled[features] = scaler.transform(rt[features])

from sklearn.impute import SimpleImputer
imputer = SimpleImputer(strategy='mean')
hist_scaled[features] = imputer.fit_transform(hist_scaled[features])
rt_scaled[features] = imputer.transform(rt_scaled[features])

# Step 4: PCA to reduce dimensionality
pca = PCA(n_components=0.95)  # keep 95% variance
X_pca = pca.fit_transform(hist_scaled[features])
X_pca_rt = pca.transform(rt_scaled[features])
print(f"PCA reduced features from {len(features)} to {X_pca.shape[1]}")

# Step 5: Train-Test Split
y = hist_scaled["label"]
X_train, X_val, y_train, y_val = train_test_split(
    X_pca, y, test_size=0.2, stratify=y, random_state=42
)

# Step 6: Train Random Forest
rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
rf.fit(X_train, y_train)
y_pred = rf.predict(X_val)
print("\nValidation Report:")
print(classification_report(y_val, y_pred))

# Step 7: Hyperparameter Tuning
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [None, 10],
    'min_samples_split': [2, 5]
}
grid = GridSearchCV(
    RandomForestClassifier(class_weight="balanced", random_state=42),
    param_grid, cv=5, scoring='f1_macro', n_jobs=-1
)
grid.fit(X_train, y_train)
rf_best = grid.best_estimator_
print("\nBest Hyperparameters:", grid.best_params_)

# Step 8: Cross-validation score
cv_scores = cross_val_score(rf_best, X_train, y_train, cv=5, scoring='f1_macro')
print("\nCross-validated F1 Macro scores:", cv_scores)
print("Mean CV F1 Macro:", cv_scores.mean())

# Step 9: Optional fine-tuning on real-time data if labeled
if "label" in rt_scaled.columns:
    rf_best.fit(X_pca_rt, rt_scaled["label"])
    print("\nModel fine-tuned on real-time labeled data.")

# Step 10: Predict on real-time data
rt_preds = rf_best.predict(X_pca_rt)
print("\nPredictions on real-time data:\n", rt_preds)

# Step 11: Save trained objects
joblib.dump(scaler, "scaler.pkl")
joblib.dump(pca, "pca.pkl")
joblib.dump(rf_best, "rf_model.pkl")
print("\nScaler, PCA, and model saved.")
