# MLB Unified Data Layer with Apache Iceberg

A comprehensive demonstration of Apache Iceberg integration with Databricks Unity Catalog using real-world MLB StatCast baseball analytics data. This project showcases both native Unity Catalog operations and external client access patterns for modern data lake architectures.

## 🎯 Overview

This project demonstrates how to build a unified data layer using Apache Iceberg that enables:
- **Vendor-neutral data access** across multiple platforms
- **Full CRUD operations** on structured data
- **Advanced baseball analytics** with real MLB StatCast data
- **External client integration** with Unity Catalog managed tables
- **Open standards** for maximum ecosystem compatibility

## 📊 Dataset

The project uses comprehensive **MLB StatCast data from the 2024 season** containing:
- **651 player records** with detailed batting statistics
- **67+ statistical columns** including traditional and advanced metrics
- **Expected statistics** (xBA, xwOBA, xSLG) for performance evaluation
- **Quality of contact metrics** (exit velocity, launch angle, barrel rate)
- **Plate discipline data** (swing/take rates, whiff percentage)
- **Advanced swing metrics** (bat speed, attack angle, swing path)

Data is sourced directly from MLB's Baseball Savant API, providing real-world analytics used by professional teams.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Unity Catalog (Governance Layer)             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │    Metadata     │  │   Permissions   │  │   Audit Logs    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Apache Iceberg Tables                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ MLB Player Stats│  │   Schema Mgmt   │  │  Time Travel    │  │
│  │   (Partitioned) │  │   Evolution     │  │   Snapshots     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Databricks    │  │  External OSS   │  │   Other Spark   │
│     Native      │  │     Spark       │  │   Platforms     │
│    Compute      │  │   (EMR, etc.)   │  │   (On-prem)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 📁 Project Structure

```
MLB Unified Data Layer with Iceberg/
├── README.md                        # This file
├── baseball_iceberg_crud_demo.ipynb # Core CRUD operations demo
├── external_client_crud.ipynb       # External client access demo
└── config.py                       # Configuration file (not included)
```

## 🚀 Getting Started

### Prerequisites

1. **Databricks Workspace** with Unity Catalog enabled
2. **Personal Access Token** with appropriate permissions
3. **Python Environment** with PySpark capabilities
4. **Unity Catalog Catalog** and schema access

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "MLB Unified Data Layer with Iceberg"
   ```

2. **Configure access (for external client demo):**
   Create a `config.py` file with your Databricks credentials:
   ```python
   # Databricks workspace configuration
   WORKSPACE_URI = "your-workspace.databricks.com"
   ACCESS_TOKEN = "your-access-token"
   UC_CATALOG_NAME = "your-catalog-name"
   ```

3. **Install dependencies (for external client):**
   ```bash
   pip install pyspark==3.5.1
   ```

## 📘 Notebooks Overview

### 1. `baseball_iceberg_crud_demo.ipynb`

**Purpose:** Demonstrates native Unity Catalog CRUD operations on Iceberg tables

**Features:**
- 🔄 **Data Loading:** Load MLB StatCast data from Baseball Savant API
- 📝 **CREATE:** Insert new player records with comprehensive metrics
- 📊 **READ:** Query and analyze player statistics with advanced analytics
- ✏️ **UPDATE:** Modify existing player data and recalculate metrics
- 🗑️ **DELETE:** Remove player records with conditional deletions
- ⚡ **Advanced Features:** Schema evolution, time travel, partitioning

**Key Analytics Queries:**
- Top performers by offensive metrics (wOBA, exit velocity, barrels)
- Power vs contact hitting analysis
- Expected vs actual performance analysis
- Plate discipline metrics
- Advanced swing analytics

### 2. `external_client_crud.ipynb`

**Purpose:** Shows how external Apache Spark clients can access Unity Catalog managed Iceberg tables

**Features:**
- 🔧 **External Setup:** Configure OSS Spark with Iceberg and Unity Catalog
- 🔐 **Authentication:** Secure REST API access using tokens
- 🌐 **Cross-Platform:** Access from any Spark-compatible platform
- 💰 **Cost Optimization:** Use external compute with managed storage
- 🔒 **Governance:** Maintain centralized control through Unity Catalog

**Architecture Benefits:**
- No vendor lock-in
- Centralized governance
- Multi-cloud compatibility
- Cost-effective external compute

## 🎮 Usage Examples

### Running the Native Demo

1. Open `baseball_iceberg_crud_demo.ipynb` in Databricks
2. Update the catalog and schema names in cell 2
3. Run all cells to see complete CRUD workflow
4. Explore the advanced analytics sections

### Running the External Client Demo

1. Ensure `config.py` is properly configured
2. Run `external_client_crud.ipynb` in any Jupyter environment
3. Observe external access to Unity Catalog managed tables
4. Experiment with CRUD operations from external clients

## 📈 Key Analytics Insights

The project demonstrates real-world baseball analytics including:

- **Power Analysis:** Exit velocity, launch angle, barrel rate
- **Contact Skills:** Batting average, BABIP, swing metrics
- **Plate Discipline:** Walk rate vs strikeout rate analysis
- **Expected Performance:** xStats vs actual performance gaps
- **Advanced Metrics:** Bat speed, swing path, attack angle

## 🔧 Technical Features

### Apache Iceberg Benefits
- **ACID Transactions:** Full consistency guarantees
- **Schema Evolution:** Add/modify columns without breaking existing queries
- **Time Travel:** Query historical data snapshots
- **Partitioning:** Efficient query performance by year
- **Hidden Partitioning:** Automatic partition management

### Unity Catalog Integration
- **Centralized Metadata:** Single source of truth for data governance
- **Fine-grained Permissions:** Column-level access control
- **Audit Logging:** Complete data lineage and access tracking
- **Cross-cloud Support:** Works across AWS, Azure, and GCP

### External Client Capabilities
- **REST API Access:** Unity Catalog REST endpoints for metadata
- **Direct Storage Access:** Read/write data files directly from S3
- **Authentication:** Token-based secure access
- **Platform Agnostic:** Works with any Spark-compatible platform

## 🌟 Use Cases

1. **Sports Analytics:** Real-time player performance analysis
2. **Partner Data Sharing:** Secure collaboration across organizations  
3. **Multi-Cloud Analytics:** Access data from different cloud platforms
4. **Legacy Integration:** Connect existing systems to modern data lakes
5. **Cost Optimization:** Use external compute for batch processing
6. **Disaster Recovery:** External access ensures business continuity


## 🙏 Acknowledgments

- **MLB Baseball Savant** for providing comprehensive StatCast data
- **Apache Iceberg** community for the powerful table format
- **Databricks** for Unity Catalog and platform capabilities

## 📞 Support

For questions or issues:
1. Check the notebook documentation and comments
2. Review Databricks Unity Catalog documentation
3. Consult Apache Iceberg documentation for table format details

---

**Built with ❤️ for the data community**
