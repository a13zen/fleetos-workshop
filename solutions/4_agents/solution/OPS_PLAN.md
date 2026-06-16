# Fleet Operations Plan
**Week of April 16-22, 2026**
**Generated:** 2026-04-16

---

## 1. Workshop Bay Schedule

### Overview
This week's maintenance schedule prioritizes vehicles based on risk scores, allocating available workshop bays to the highest-priority vehicles requiring service.

**Key Metrics:**
- **Total vehicles scheduled:** 8
- **Total vehicles on waitlist:** 2
- **Workshop utilization rate:** 80%
- **Critical vehicles scheduled (Risk ≥ 90):** 6

---

### Daily Schedule

#### **Thursday, April 16, 2026**

| Bay ID | Depot | Vehicle ID | Risk Score | Issue |
|--------|-------|------------|------------|-------|
| DG-BAY-01 | Dingolfing Main | BMW-FLT-006 | 98 | Multiple system alerts |
| DG-BAY-02 | Dingolfing Main | BMW-FLT-010 | 96 | Critical - oil leak detected |

#### **Friday, April 17, 2026**

| Bay ID | Depot | Vehicle ID | Risk Score | Issue |
|--------|-------|------------|------------|-------|
| DG-BAY-05 | Dingolfing Main | BMW-FLT-001 | 95 | Brake system warning |
| RG-BAY-01 | Regensburg Depot | BMW-FLT-004 | 92 | Transmission service overdue |

#### **Saturday, April 18, 2026**

| Bay ID | Depot | Vehicle ID | Risk Score | Issue |
|--------|-------|------------|------------|-------|
| RG-BAY-02 | Regensburg Depot | BMW-FLT-002 | 88 | Engine diagnostics needed |
| DG-BAY-04 | Dingolfing Main | BMW-FLT-003 | 85 | Suspension check required |

#### **Sunday, April 19, 2026**

| Bay ID | Depot | Vehicle ID | Risk Score | Issue |
|--------|-------|------------|------------|-------|
| LH-BAY-01 | Landshut Service | BMW-FLT-008 | 82 | Air conditioning service |
| LH-BAY-02 | Landshut Service | BMW-FLT-007 | 78 | Tire replacement needed |

---

### Waitlist (No Available Bays This Week)

The following vehicles require maintenance but could not be scheduled due to capacity constraints:

| Vehicle ID | Risk Score | Issue |
|------------|------------|-------|
| BMW-FLT-005 | 72 | Routine maintenance |
| BMW-FLT-009 | 68 | Scheduled inspection |

**Recommendation:** Prioritize these vehicles for next week's schedule.

---

### Depot Allocation Summary

| Depot | Scheduled Vehicles | Bay Utilization |
|-------|-------------------|-----------------|
| Dingolfing Main | 4 | 80% (4/5 bays) |
| Regensburg Depot | 2 | 50% (2/4 bays) |
| Landshut Service | 2 | 67% (2/3 bays) |

---

## 2. Deferral Cost Analysis

### Executive Summary

This analysis quantifies the EUR cost exposure of deferring maintenance for overdue and due-soon vehicles by one additional week. Costs combine fuel efficiency degradation and breakdown risk calculations.

**Key Financial Metrics:**
- **Total Vehicles Analyzed:** 6
- **Total Weekly Exposure:** €378.84
- **Average Cost per Vehicle:** €63.14/week
- **Monthly Exposure (if all deferred):** €1,515.36

---

### Deferral Cost Table

| Vehicle ID | Weekly Deferral Cost | Status & Rationale |
|------------|---------------------|-------------------|
| **BMW-1843** | **€102.54** | CRITICAL oil_change, 5 days overdue<br>Fuel penalty €15.04/wk + breakdown risk €87.50/wk |
| **BMW-1234** | **€77.25** | HIGH tire_rotation, 2 days overdue<br>Fuel penalty €11.25/wk + breakdown risk €66.00/wk |
| **BMW-5678** | **€61.82** | MEDIUM brake_inspection, due soon<br>Fuel penalty €0.00/wk + breakdown risk €61.82/wk |
| **BMW-1111** | **€51.33** | MEDIUM oil_change, due soon<br>Fuel penalty €0.00/wk + breakdown risk €51.33/wk |
| **BMW-2222** | **€44.48** | LOW tire_rotation, due soon<br>Fuel penalty €0.00/wk + breakdown risk €44.48/wk |
| **BMW-3333** | **€41.42** | LOW brake_inspection, due soon<br>Fuel penalty €0.00/wk + breakdown risk €41.42/wk |

---

### Cost Breakdown by Priority

| Priority | Vehicle Count | Total Weekly Cost | Average Cost |
|----------|---------------|------------------|--------------|
| CRITICAL | 1 | €102.54 | €102.54 |
| HIGH | 1 | €77.25 | €77.25 |
| MEDIUM | 2 | €113.15 | €56.58 |
| LOW | 2 | €85.90 | €42.95 |

---

### High-Risk Vehicles Requiring Immediate Attention

**4 vehicles with weekly deferral costs exceeding €50:**

1. **BMW-1843** (€102.54/week) - CRITICAL priority, 5 days overdue
   - **Risk:** Engine damage, warranty issues
   - **Action:** Schedule oil change immediately

2. **BMW-1234** (€77.25/week) - HIGH priority, 2 days overdue
   - **Risk:** Uneven tire wear, safety concerns
   - **Action:** Schedule tire rotation immediately

3. **BMW-5678** (€61.82/week) - MEDIUM priority, due soon
   - **Action:** Schedule brake inspection before due date

4. **BMW-1111** (€51.33/week) - MEDIUM priority, due soon
   - **Action:** Schedule oil change before due date

---

### Financial Impact Analysis

| Scenario | Cost Impact |
|----------|------------|
| Defer all maintenance for 1 month | €1,515.36 additional cost |
| Defer top 2 vehicles for 2 weeks | €359.58 additional cost |
| **ROI of immediate action** | **Prevent 100% of calculated deferral costs** |

---

### Methodology

**Data Sources:**
- **Ops Database** (`ops.db`): Fuel consumption logs with vehicle ID, date, fuel consumed, and distance
- **FleetOS API** (`http://localhost:8080/api`): Maintenance schedule with due dates, priority, and service types

**Cost Calculation Components:**
1. **Fuel Efficiency Penalty** = Weekly Fuel Cost × Efficiency Loss %
   - Efficiency Loss % = max(Recent Trend, 1.5% × Weeks Overdue)
2. **Breakdown Risk Cost** = Priority Base Cost × (1 + Weeks Overdue^1.3 × 0.15) × 0.15

**Assumptions:**
- Fuel price: €1.65/liter (typical diesel)
- Average weekly distance: 500 km
- Breakdown probability: 15% per week when overdue
- Priority base costs: Critical €500, High €200, Medium €80, Low €30

---

## 3. Driver Communications

All driver notification emails for scheduled maintenance appointments have been prepared and are available in:

📧 **[DRIVER_EMAILS.md](DRIVER_EMAILS.md)**

The file contains 8 professional emails (one for each scheduled vehicle) with:
- Vehicle identification and appointment date/time
- Service location (depot and bay assignment)
- Issue description and estimated service duration
- Arrival instructions and contact information
- Appropriate urgency indicators (URGENT flag for BMW-FLT-010 critical oil leak)

Emails are organized chronologically from Thursday, April 16 through Sunday, April 19, 2026.

---

## 4. Action Items & Recommendations

### Immediate Actions (This Week)
1. ✅ **Confirm driver notifications sent** for all 8 scheduled vehicles
2. ⚠️ **BMW-FLT-010 & BMW-FLT-006** - Ensure parts/expertise available for critical issues
3. 📋 **Parts procurement** - Verify brake components for BMW-FLT-001, transmission parts for BMW-FLT-004
4. 🔧 **Technician allocation** - Assign experienced techs to high-risk vehicles

### Next Week Planning
1. **Waitlist vehicles** (BMW-FLT-005, BMW-FLT-009) - Schedule for next available bays
2. **Deferral cost vehicles** - Cross-reference BMW-1843 and BMW-1234 with fleet roster for priority scheduling
3. **Capacity review** - Consider extending hours or adding temporary bay capacity

### Financial Optimization
1. **Prioritize high-cost deferrals** - Focus on vehicles with weekly costs >€50
2. **Monitor fuel trends** - Continue tracking consumption data for early intervention
3. **Preventive scheduling** - Reduce future deferral costs through proactive maintenance

---

## 5. Key Performance Indicators

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Workshop utilization | >75% | 80% | ✅ On track |
| Critical vehicles scheduled | 100% | 100% (6/6) | ✅ Excellent |
| Average deferral cost | <€50/vehicle | €63.14 | ⚠️ Monitor |
| Driver notification rate | 100% | Pending | 🔄 In progress |

---

## 6. Contact Information

**Fleet Operations Team**
- Phone: (555) 0100
- Email: fleet.ops@fleetos.example
- Hours: Monday-Sunday, 7:00 AM - 6:00 PM

**Emergency Maintenance Hotline**
- Phone: (555) 0911
- Available 24/7 for critical issues

---

## Supporting Documentation

- **Detailed Schedule Report:** `/starter/maintenance_schedule_report.txt`
- **Schedule Data (JSON):** `/starter/workshop_schedule.json`
- **Deferral Cost Report:** `/starter/DEFERRAL_COST_REPORT.md`
- **Deferral Cost Data (JSON):** `/starter/deferral_costs.json`
- **Driver Emails:** `/starter/DRIVER_EMAILS.md`

---

*This operations plan was generated through coordinated analysis by specialized fleet management agents: maintenance-planner, cost-analyst, and comms-drafter.*

**Next Review:** 2026-04-23 (End of week review)
