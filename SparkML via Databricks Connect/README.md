# 🧪 Databricks Connect: Distributed ML Demo

This demo showcases how to leverage **Databricks Connect** for distributed machine learning workflows. It illustrates the progression from local model training to distributed training using `pyspark.ml.connect`, highlighting the current limitations and upcoming enhancements in Spark 4.0.

## 📚 Notebooks Overview

### `00_databricks_connect.ipynb` — Setup and Spark Session Initialization

- Establishes a connection to a remote Databricks cluster using `DatabricksSession`.
- Demonstrates basic DataFrame operations to validate the connection.

### `01_prepare_data.ipynb` — Data Preparation

- Loads the breast cancer dataset from `sklearn.datasets`.
- Converts the dataset into a Spark DataFrame.
- Writes the DataFrame to Unity Catalog for centralized access.

### `02_local_training.ipynb` — Local Model Training with MLflow Logging

- Reads data from Unity Catalog using Databricks Connect.
- Trains a logistic regression model locally using `scikit-learn`.
- Logs parameters, metrics, and the model itself to MLflow, with the tracking server hosted on Databricks.

### `03_pyspark_ml_failure.ipynb` — Attempted Distributed Training with `pyspark.ml`

- Attempts to perform distributed training using the classic `pyspark.ml` API.
- Encounters failures due to the lack of JVM support in the Spark Connect client.
- Highlights the current limitations of using `pyspark.ml` with Databricks Connect in Spark 3.5.x.

### `04_pyspark_ml_connect.ipynb` — Successful Distributed Training with `pyspark.ml.connect`

- Utilizes the newer `pyspark.ml.connect` API designed for Spark Connect.
- Successfully performs distributed training on the Databricks cluster.
- Logs the experiment to MLflow and registers the model in Unity Catalog.

## 🚧 Known Limitations

- The `pyspark.ml.connect` API currently supports a very limited set of algorithms and transformers.
- The classic `pyspark.ml` API is not compatible with Spark Connect in Spark 3.5.x due to its reliance on the JVM.

## 🔮 Looking Ahead: Spark 4.0

Exciting developments are underway to bring full support for the classic `pyspark.ml` API to Spark Connect, eliminating the need for separate APIs. This enhancement is being tracked in [SPARK-49907](https://issues.apache.org/jira/browse/SPARK-49907), with active development in [PR #48791](https://github.com/apache/spark/pull/48791).

## 📎 References

- [Databricks Connect for Python](https://docs.databricks.com/dev-tools/databricks-connect/python/)
- [Distributed ML with Spark Connect](https://docs.databricks.com/machine-learning/train-model/distributed-training/distributed-ml-for-spark-connect)
- [Spark Connect Overview for Spark 4.0](spark.apache.org/docs/4.0.0-preview2/spark-connect-overview.html)
- [SPARK-49907: Support spark.ml on Connect](https://issues.apache.org/jira/browse/SPARK-49907)
- [Apache Spark PR #48791](https://github.com/apache/spark/pull/48791)