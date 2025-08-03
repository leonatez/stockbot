# Database Views Documentation for Stock Market Data Crawling System

## System Overview
This documentation describes database views for a Vietnamese stock market data crawling and analysis system. The system crawls financial news articles from various sources, processes them with AI to extract stock sentiment and mentions, and stores comprehensive stock market data including prices, trading ticks, and corporate events.

## Database Views Purpose and Usage

### 1. `v_total_sources` - Total Sources Counter
**Purpose**: Provides the complete count of all data crawling sources configured in the system.

**Business Context**: 
- Represents all news websites, financial portals, or data feeds that the system is configured to monitor
- Used for system capacity planning and monitoring
- Helps administrators understand the scope of data collection

**Query**: `SELECT * FROM v_total_sources;`
**Returns**: Single row with `total_sources` (integer)

**Example Usage**:
- Dashboard widgets showing "Total Configured Sources: 15"
- System health monitoring
- Capacity planning reports

### 2. `v_active_sources` - Active Sources Counter
**Purpose**: Counts only the sources that are currently active and being crawled.

**Business Context**:
- Sources can be temporarily disabled for maintenance, rate limiting, or content quality issues
- Critical metric for operational monitoring
- Indicates actual data collection capacity vs. configured capacity

**Query**: `SELECT * FROM v_active_sources;`
**Returns**: Single row with `active_sources` (integer)

**Example Usage**:
- Real-time monitoring: "12 of 15 sources are currently active"
- Alerting when active sources drop below threshold
- Data quality assessments

### 3. `v_recent_posts` - Recent Posts Counter
**Purpose**: Counts articles/posts crawled and processed in the last 7 days.

**Business Context**:
- Measures system activity and data freshness
- Critical for ensuring continuous data flow
- Used to identify potential crawling issues or source problems
- Helps validate that AI processing pipeline is functioning

**Query**: `SELECT * FROM v_recent_posts;`
**Returns**: Single row with `recent_posts_count` (integer)

**Example Usage**:
- Dashboard: "342 articles processed this week"
- Data freshness monitoring
- Performance trending analysis
- Alerting when daily/weekly post counts drop significantly

### 4. `v_sources_list` - Sources Management View
**Purpose**: Provides a prioritized list of all sources with key management information.

**Business Context**:
- Administrative interface for source management
- Active sources are prioritized (sorted first) for operational focus
- Shows when sources were added to track system growth
- Essential for troubleshooting and maintenance

**Query**: `SELECT * FROM v_sources_list;`
**Returns**: Multiple rows with `name`, `created_at`, `status`
**Sorting**: Active sources first, then by creation date (newest first)

**Example Usage**:
- Admin dashboard source list
- Source status monitoring interface
- Maintenance scheduling (identify oldest sources)
- Quick identification of inactive sources requiring attention

### 5. `v_dashboard_stats` - Combined Statistics View
**Purpose**: Aggregates all key metrics into a single query for dashboard efficiency.

**Business Context**:
- Optimizes dashboard loading by combining multiple statistics
- Provides complete system health snapshot
- Reduces database load compared to separate queries
- Ideal for API endpoints serving dashboard data

**Query**: `SELECT * FROM v_dashboard_stats;`
**Returns**: Single row with `total_sources`, `active_sources`, `recent_posts_count`

**Example Usage**:
- Main dashboard summary widget
- System status API endpoint
- Health check monitoring
- Executive reporting summaries

## Data Flow Context

### How These Views Relate to the Stock Analysis Pipeline:

1. **Sources** → **Posts** → **AI Analysis** → **Stock Mentions** → **Trading Insights**

2. **View Usage in Pipeline Monitoring**:
   - `v_active_sources`: Ensures data input channels are functioning
   - `v_recent_posts`: Validates continuous data processing
   - Combined views: Provide complete pipeline health status

### Typical Dashboard Layout:
```
┌─────────────────┬─────────────────┬─────────────────┐
│ Total Sources   │ Active Sources  │ Recent Posts    │
│      15         │       12        │      342        │
└─────────────────┴─────────────────┴─────────────────┘

┌─────────────────────────────────────────────────────┐
│ Source Status                                       │
│ ✅ VnExpress Finance    (Active)   - Jan 15, 2025  │
│ ✅ CafeF.vn            (Active)   - Jan 10, 2025  │
│ ❌ InvestingVN         (Inactive) - Dec 20, 2024  │
└─────────────────────────────────────────────────────┘
```

## Performance Considerations

- **Views are cached**: Results update automatically when underlying data changes
- **Efficient for dashboards**: Single queries instead of complex joins
- **Indexing**: Underlying tables have indexes on `status`, `created_date` for optimal view performance
- **Real-time safe**: Views reflect current data state without caching delays

## Alert Thresholds (Suggested)

- **Active Sources**: Alert if < 80% of total sources are active
- **Recent Posts**: Alert if count drops > 50% compared to previous week
- **Source Status**: Alert when new sources are added or existing ones go inactive

## Integration Points

These views are designed for:
- Dashboard APIs (REST/GraphQL endpoints)
- Monitoring systems (Grafana, DataDog)
- Administrative interfaces
- Automated reporting systems
- Health check endpoints for DevOps monitoring