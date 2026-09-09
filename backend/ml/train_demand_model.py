
import joblib
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATASET_DIR = os.path.join(
    BASE_DIR,
    "datasets"
)

ML_DIR = os.path.join(
    BASE_DIR,
    "ml"
)

HISTORICAL_PATH = os.path.join(
    DATASET_DIR,
    "demand_history.csv"
)

MARKET_PATH = os.path.join(
    DATASET_DIR,
    "market_dataset.csv"
)

MODEL_PATH = os.path.join(
    ML_DIR,
    "demand_model.pkl"
)


# ============================================================
# CONFIGURATION
# ============================================================

TEST_SIZE = 0.20

RANDOM_STATE = 42

MIN_RECORDS = 20


# ============================================================
# START
# ============================================================

print()
print("======================================================")
print("       PRICEPILOT AI - DEMAND MODEL TRAINING")
print("======================================================")
print()


# ============================================================
# CREATE ML DIRECTORY
# ============================================================

os.makedirs(
    ML_DIR,
    exist_ok=True
)


# ============================================================
# CHECK DATASETS
# ============================================================

print("Checking datasets...")


if not os.path.exists(HISTORICAL_PATH):

    raise FileNotFoundError(
        "\nDemand history dataset not found.\n"
        f"Expected:\n{HISTORICAL_PATH}\n"
    )


if not os.path.exists(MARKET_PATH):

    raise FileNotFoundError(
        "\nMarket dataset not found.\n"
        f"Expected:\n{MARKET_PATH}\n"
    )


# ============================================================
# LOAD DATA
# ============================================================

print()
print("Loading demand history...")

historical = pd.read_csv(
    HISTORICAL_PATH
)

print(
    f"Historical records: {len(historical)}"
)


print()
print("Loading market dataset...")

market = pd.read_csv(
    MARKET_PATH
)

print(
    f"Market records: {len(market)}"
)


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

historical.columns = (
    historical.columns
    .str.strip()
    .str.lower()
)

market.columns = (
    market.columns
    .str.strip()
    .str.lower()
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_historical = [
    "date",
    "product_name",
    "category",
    "price",
    "stock",
    "units_sold",
    "competitor_price",
    "discount"
]


missing = [
    column
    for column in required_historical
    if column not in historical.columns
]


if missing:

    raise ValueError(
        "Demand history is missing columns: "
        + ", ".join(missing)
    )


required_market = [
    "date",
    "product_name"
]


missing_market = [
    column
    for column in required_market
    if column not in market.columns
]


if missing_market:

    raise ValueError(
        "Market dataset is missing columns: "
        + ", ".join(missing_market)
    )


# ============================================================
# CLEAN DATES
# ============================================================

historical["date"] = pd.to_datetime(
    historical["date"],
    errors="coerce"
)

market["date"] = pd.to_datetime(
    market["date"],
    errors="coerce"
)


historical = historical.dropna(
    subset=["date"]
)

market = market.dropna(
    subset=["date"]
)


# ============================================================
# CLEAN PRODUCT NAMES
# ============================================================

historical["product_name"] = (
    historical["product_name"]
    .astype(str)
    .str.strip()
)


market["product_name"] = (
    market["product_name"]
    .astype(str)
    .str.strip()
)


# ============================================================
# CLEAN CATEGORY
# ============================================================

historical["category"] = (
    historical["category"]
    .astype(str)
    .str.strip()
)


# ============================================================
# CONVERT NUMERIC COLUMNS
# ============================================================

historical_numeric = [
    "price",
    "stock",
    "units_sold",
    "competitor_price",
    "discount"
]


for column in historical_numeric:

    historical[column] = pd.to_numeric(
        historical[column],
        errors="coerce"
    )


# ============================================================
# REMOVE INVALID TARGET RECORDS
# ============================================================

historical = historical.dropna(
    subset=["units_sold"]
)


historical["units_sold"] = (
    historical["units_sold"]
    .clip(lower=0)
)


# ============================================================
# FILL BASIC PRODUCT VALUES
# ============================================================

for column in [
    "price",
    "stock",
    "competitor_price",
    "discount"
]:

    historical[column] = (
        historical[column]
        .fillna(
            historical[column].median()
        )
    )


# ============================================================
# SORT BY PRODUCT + DATE
# ============================================================

historical = (
    historical
    .sort_values(
        [
            "product_name",
            "date"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# TIME FEATURES
# ============================================================

print()
print("Creating time features...")


historical["month"] = (
    historical["date"].dt.month
)


historical["day_of_week"] = (
    historical["date"].dt.dayofweek
)


historical["day_of_year"] = (
    historical["date"].dt.dayofyear
)


historical["week_of_year"] = (
    historical["date"].dt.isocalendar().week
    .astype(int)
)


historical["quarter"] = (
    historical["date"].dt.quarter
)


# ============================================================
# CYCLICAL TIME FEATURES
# ============================================================

historical["month_sin"] = (
    __import__("numpy").sin(
        2
        * __import__("numpy").pi
        * historical["month"]
        / 12
    )
)


historical["month_cos"] = (
    __import__("numpy").cos(
        2
        * __import__("numpy").pi
        * historical["month"]
        / 12
    )
)


historical["day_of_week_sin"] = (
    __import__("numpy").sin(
        2
        * __import__("numpy").pi
        * historical["day_of_week"]
        / 7
    )
)


historical["day_of_week_cos"] = (
    __import__("numpy").cos(
        2
        * __import__("numpy").pi
        * historical["day_of_week"]
        / 7
    )
)


# ============================================================
# DEMAND LAG FEATURES
# ============================================================

print("Creating demand lag features...")


grouped_demand = (
    historical
    .groupby("product_name")["units_sold"]
)


historical["lag_1"] = (
    grouped_demand
    .shift(1)
)


historical["lag_2"] = (
    grouped_demand
    .shift(2)
)


historical["lag_3"] = (
    grouped_demand
    .shift(3)
)


historical["lag_7"] = (
    grouped_demand
    .shift(7)
)


historical["lag_14"] = (
    grouped_demand
    .shift(14)
)


historical["lag_30"] = (
    grouped_demand
    .shift(30)
)


# ============================================================
# ROLLING FEATURES
# ============================================================

print("Creating rolling demand features...")


historical["rolling_3"] = (
    historical
    .groupby("product_name")["units_sold"]
    .transform(
        lambda x:
        x.shift(1)
        .rolling(
            3,
            min_periods=1
        )
        .mean()
    )
)


historical["rolling_7"] = (
    historical
    .groupby("product_name")["units_sold"]
    .transform(
        lambda x:
        x.shift(1)
        .rolling(
            7,
            min_periods=1
        )
        .mean()
    )
)


historical["rolling_14"] = (
    historical
    .groupby("product_name")["units_sold"]
    .transform(
        lambda x:
        x.shift(1)
        .rolling(
            14,
            min_periods=1
        )
        .mean()
    )
)


historical["rolling_30"] = (
    historical
    .groupby("product_name")["units_sold"]
    .transform(
        lambda x:
        x.shift(1)
        .rolling(
            30,
            min_periods=1
        )
        .mean()
    )
)


# ============================================================
# DEMAND TREND
# ============================================================

historical["demand_trend"] = (
    historical["rolling_7"]
    -
    historical["rolling_30"]
)


# ============================================================
# PREPARE MARKET DATA
# ============================================================

print()
print("Preparing market data...")


market_columns = [
    "date",
    "product_name",
    "competitor_avg_price",
    "market_demand_index",
    "competitor_count",
    "market_trend"
]


available_market_columns = [
    column
    for column in market_columns
    if column in market.columns
]


market = market[
    available_market_columns
].copy()


# ============================================================
# MARKET NUMERIC VALUES
# ============================================================

for column in [
    "competitor_avg_price",
    "market_demand_index",
    "competitor_count"
]:

    if column in market.columns:

        market[column] = pd.to_numeric(
            market[column],
            errors="coerce"
        )


# ============================================================
# MARKET TREND ENCODING
# ============================================================

market_trend_map = {

    "falling": 0,

    "stable": 1,

    "rising": 2,

    "high": 3
}


if "market_trend" in market.columns:

    market["market_trend"] = (
        market["market_trend"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(market_trend_map)
    )

else:

    market["market_trend"] = 1


# ============================================================
# MERGE MARKET DATA
# ============================================================

print()
print("Combining demand and market data...")


data = pd.merge(
    historical,
    market,
    on=[
        "date",
        "product_name"
    ],
    how="left"
)


# ============================================================
# MARKET VALUES
# ============================================================

if "competitor_avg_price" not in data.columns:

    data["competitor_avg_price"] = (
        data["competitor_price"]
    )


if "market_demand_index" not in data.columns:

    data["market_demand_index"] = 50


if "competitor_count" not in data.columns:

    data["competitor_count"] = 1


if "market_trend" not in data.columns:

    data["market_trend"] = 1


data["competitor_avg_price"] = (
    data["competitor_avg_price"]
    .fillna(
        data["competitor_price"]
    )
)


data["competitor_avg_price"] = (
    data["competitor_avg_price"]
    .fillna(
        data["price"]
    )
)


data["market_demand_index"] = (
    data["market_demand_index"]
    .fillna(50)
)


data["competitor_count"] = (
    data["competitor_count"]
    .fillna(1)
)


data["market_trend"] = (
    data["market_trend"]
    .fillna(1)
)


# ============================================================
# CATEGORY ENCODING
# ============================================================

print()
print("Encoding categories...")


categories = sorted(
    data["category"]
    .dropna()
    .unique()
)


category_map = {
    category: index + 1
    for index, category
    in enumerate(categories)
}


data["category_code"] = (
    data["category"]
    .map(category_map)
    .fillna(0)
)


# ============================================================
# NUMERIC FEATURE CLEANING
# ============================================================

numeric_columns = [

    "price",
    "stock",
    "competitor_price",
    "discount",

    "competitor_avg_price",
    "market_demand_index",
    "competitor_count",
    "market_trend",

    "month",
    "day_of_week",
    "day_of_year",
    "week_of_year",
    "quarter",

    "month_sin",
    "month_cos",

    "day_of_week_sin",
    "day_of_week_cos",

    "lag_1",
    "lag_2",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_30",

    "rolling_3",
    "rolling_7",
    "rolling_14",
    "rolling_30",

    "demand_trend",

    "category_code"
]


for column in numeric_columns:

    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )


# ============================================================
# PRODUCT-WISE MEDIAN FILL
# ============================================================

print("Handling missing demand history...")


lag_columns = [

    "lag_1",
    "lag_2",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_30",

    "rolling_3",
    "rolling_7",
    "rolling_14",
    "rolling_30"
]


global_demand_median = (
    data["units_sold"]
    .median()
)


if pd.isna(global_demand_median):

    global_demand_median = 0


for column in lag_columns:

    data[column] = (
        data
        .groupby("product_name")[column]
        .transform(
            lambda x:
            x.fillna(
                x.median()
            )
        )
    )


    data[column] = (
        data[column]
        .fillna(
            global_demand_median
        )
    )


data["demand_trend"] = (
    data["demand_trend"]
    .fillna(0)
)


# ============================================================
# FEATURE LIST
# ============================================================

features = [

    "price",
    "stock",
    "competitor_price",
    "discount",

    "category_code",

    "competitor_avg_price",
    "market_demand_index",
    "competitor_count",
    "market_trend",

    "month",
    "day_of_week",
    "day_of_year",
    "week_of_year",
    "quarter",

    "month_sin",
    "month_cos",

    "day_of_week_sin",
    "day_of_week_cos",

    "lag_1",
    "lag_2",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_30",

    "rolling_3",
    "rolling_7",
    "rolling_14",
    "rolling_30",

    "demand_trend"
]


# ============================================================
# CREATE X / Y
# ============================================================

X = data[
    features
].copy()


y = data[
    "units_sold"
].copy()


X = X.apply(
    pd.to_numeric,
    errors="coerce"
)


X = X.replace(
    [float("inf"), float("-inf")],
    0
)


X = X.fillna(0)


y = pd.to_numeric(
    y,
    errors="coerce"
)


y = y.fillna(
    global_demand_median
)


# ============================================================
# CHECK DATA
# ============================================================

print()
print("======================================================")
print("                 TRAINING DATA")
print("======================================================")


print(
    f"Total records : {len(data)}"
)


print(
    f"Products      : "
    f"{data['product_name'].nunique()}"
)


print(
    f"Features      : {len(features)}"
)


if len(data) < MIN_RECORDS:

    raise ValueError(
        f"Only {len(data)} records were found. "
        f"At least {MIN_RECORDS} records are recommended "
        "for training the demand model."
    )


# ============================================================
# CHRONOLOGICAL TRAIN / TEST SPLIT
# ============================================================

print()
print("Creating chronological train/test split...")


sorted_indices = (
    data["date"]
    .sort_values()
    .index
)


split_position = int(
    len(sorted_indices)
    * (1 - TEST_SIZE)
)


train_indices = (
    sorted_indices[
        :split_position
    ]
)


test_indices = (
    sorted_indices[
        split_position:
    ]
)


X_train = X.loc[
    train_indices
]


X_test = X.loc[
    test_indices
]


y_train = y.loc[
    train_indices
]


y_test = y.loc[
    test_indices
]


print(
    f"Training samples : {len(X_train)}"
)


print(
    f"Testing samples  : {len(X_test)}"
)


# ============================================================
# TRAIN MODEL
# ============================================================

print()
print("Training Random Forest demand model...")


model = RandomForestRegressor(

    n_estimators=300,

    max_depth=15,

    min_samples_leaf=2,

    max_features="sqrt",

    random_state=RANDOM_STATE,

    n_jobs=-1
)


model.fit(
    X_train,
    y_train
)


# ============================================================
# PREDICTION
# ============================================================

print()
print("Evaluating model...")


predictions = model.predict(
    X_test
)


# Never allow negative demand
predictions = (
    predictions
    .clip(min=0)
)


# ============================================================
# METRICS
# ============================================================

mae = mean_absolute_error(
    y_test,
    predictions
)


rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5


r2 = r2_score(
    y_test,
    predictions
)


# ============================================================
# RESULTS
# ============================================================

print()
print("======================================================")
print("              DEMAND MODEL EVALUATION")
print("======================================================")


print(
    f"MAE  : {mae:.2f}"
)


print(
    f"RMSE : {rmse:.2f}"
)


print(
    f"R2   : {r2:.4f}"
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print()
print("======================================================")
print("                FEATURE IMPORTANCE")
print("======================================================")


feature_importance = pd.DataFrame({

    "feature":
        features,

    "importance":
        model.feature_importances_

})


feature_importance = (
    feature_importance
    .sort_values(
        "importance",
        ascending=False
    )
)


for _, row in feature_importance.iterrows():

    print(
        f"{row['feature']:25s}"
        f"{row['importance']:.4f}"
    )


# ============================================================
# MODEL METADATA
# ============================================================

model_package = {

    "model":
        model,

    "features":
        features,

    "category_map":
        category_map,

    "market_trend_map":
        market_trend_map,

    "metrics": {

        "mae":
            float(mae),

        "rmse":
            float(rmse),

        "r2":
            float(r2)

    },

    "training_info": {

        "records":
            int(len(data)),

        "products":
            int(
                data["product_name"]
                .nunique()
            ),

        "training_samples":
            int(len(X_train)),

        "testing_samples":
            int(len(X_test))

    }

}


# ============================================================
# SAVE MODEL
# ============================================================

print()
print("Saving trained model...")


joblib.dump(
    model_package,
    MODEL_PATH
)


if not os.path.exists(
    MODEL_PATH
):

    raise RuntimeError(
        "Model file was not created."
    )


# ============================================================
# VERIFY MODEL
# ============================================================

print()
print("Testing saved model...")


loaded_package = joblib.load(
    MODEL_PATH
)


loaded_model = (
    loaded_package["model"]
)


test_prediction = loaded_model.predict(
    X_test.iloc[:1]
)


print(
    "Sample prediction:",
    round(
        max(
            0,
            float(
                test_prediction[0]
            )
        ),
        2
    )
)


# ============================================================
# FINAL
# ============================================================

print()
print("======================================================")
print("          MODEL TRAINING COMPLETED")
print("======================================================")


print()
print("Model saved to:")

print(
    MODEL_PATH
)


print()
print("Features saved:")

for feature in features:

    print(
        f"  - {feature}"
    )


print()
print("Category mapping:")

for category, code in category_map.items():

    print(
        f"  {category} -> {code}"
    )


print()
print("You can now start FastAPI and test:")

print(
    "POST /demand/forecast"
)

print()

