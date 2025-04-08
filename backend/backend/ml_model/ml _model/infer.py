# infer.py
import pandas as pd
import joblib
from sklearn.impute import SimpleImputer

# Manual protocol mapping
protocol_map = {"TCP": 6, "UDP": 17, "ICMP": 1}

def model_predict(rt_csv_path):
    # 1. Load real-time data
    df = pd.read_csv(rt_csv_path)

    # 2. Encode protocol strings to numbers
    if df["protocol"].dtype == object:
        df["protocol"] = df["protocol"].map(protocol_map).fillna(-1).astype(int)

    # 3. Load artifacts
    scaler = joblib.load("scaler.pkl")
    pca    = joblib.load("pca.pkl")
    model  = joblib.load("rf_model.pkl")

    # 4. Select features used in training
    features = scaler.feature_names_in_.tolist()

    # 5. Scale features
    X = scaler.transform(df[features])

    # 6. Impute missing values (in case any remain)
    imputer = SimpleImputer(strategy="mean")
    X = imputer.fit_transform(X)

    # 7. PCA transform
    X = pca.transform(X)

    # 8. Predict
    preds = model.predict(X)
    return preds
#below is for testing the model_predict function as i want to check wheter csv genearted will match the test csv file realtime_flow_features.csv
if __name__ == "__main__":
    preds = model_predict("realtime_flow_features.csv")
    print("Predictions:", preds)
