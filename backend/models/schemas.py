from pydantic import BaseModel
from typing import Optional


# ---------------------------------------------------------------------------
# Pydantic sub-models
# ---------------------------------------------------------------------------

class WorkerModel(BaseModel):
    id: str; name: str; platform: str; zone: str
    status: str; shift_started: str; days_covered: int; member_since: str


class PlanTriggersModel(BaseModel):
    rainfall_mm_per_hr: float; aqi_ug_m3: float; wind_speed_km_h: float


class PlanModel(BaseModel):
    plan_name: str; plan_type: str; premium_inr: float; premium_period: str
    coverage_cap_inr: float; max_claims_per_week: int; claims_used_this_week: int
    valid_until: str; claim_process: str; triggers: PlanTriggersModel
    exclusions_summary: list[str]


class ComponentScoresModel(BaseModel):
    rainfall_score: float; aqi_score: float; wind_score: float


class IMDBandsModel(BaseModel):
    rainfall: str; aqi: str; wind_speed: str


class ConfidenceModel(BaseModel):
    score: float; label: str


class RiskTrendModel(BaseModel):
    trend: str; message: str
    eta_hours: Optional[int]
    contributing_factors: list[str]
    confidence: float


class ExclusionModel(BaseModel):
    is_excluded: bool; exclusion_code: str; reason: str
    is_partial: bool; reduction_pct: float
    applicable_clauses: list[str]


class FraudFlagModel(BaseModel):
    rule_code: str; weight: int; description: str


class FraudCheckModel(BaseModel):
    raw_score:         int
    fraud_score:       float    # 0.0–1.0 (v4)
    fraud_flag:        bool     # v4
    verdict:           str
    flag_codes:        list[str]
    reason:            str
    fraud_explanation: str      # v4
    auto_approve:      bool
    flags:             list[FraudFlagModel]


class ActuarialModel(BaseModel):
    pure_premium:           Optional[float]
    loaded_premium:         Optional[float]
    premium_adequacy:       Optional[str]
    expected_loss_ratio:    Optional[float]
    claims_reserve:         Optional[float]
    expected_weekly_payout: Optional[float]
    # v4 NEW
    event_probability:  Optional[float]
    expected_loss:      Optional[float]
    dynamic_premium:    Optional[float]
    risk_loading:       Optional[float]
    claim_adjustment:   Optional[float]


class PayoutDeliveryModel(BaseModel):
    method: str; upi_id_masked: str; eta_hours: int


# ---------------------------------------------------------------------------
# Endpoint response models
# ---------------------------------------------------------------------------

class CurrentRiskModel(BaseModel):
    risk_score: float; risk_level: str; primary_hazard: str
    rainfall: float; aqi: float; wind_speed: float
    imd_bands: IMDBandsModel; confidence: ConfidenceModel
    risk_trend: RiskTrendModel
    # v4
    trend: str; trend_velocity: float
    anomaly_flag: bool; anomaly_severity: str
    predicted_risk_score: float; predicted_risk_level: str
    risk_category_reason: str; decision_explanation: str


class PayoutStatusModel(BaseModel):
    triggered: bool; tier_label: str; payout_percentage: float
    gross_payout: float; platform_fee: float; net_payout: float
    # v4
    risk_loading: float; claim_adjustment: float; final_payout: float
    effective_payout: float; amount_inr: float
    payout_explanation: str
    exclusion: ExclusionModel; fraud_check: FraudCheckModel
    message: str; delivery: PayoutDeliveryModel


class DashboardResponse(BaseModel):
    worker: WorkerModel; plan: PlanModel
    current_risk: CurrentRiskModel; payout_status: PayoutStatusModel
    actuarial: ActuarialModel; last_updated: str


class RiskResponse(BaseModel):
    rainfall: float; aqi: float; wind_speed: float; scenario_label: str
    component_scores: ComponentScoresModel
    risk_score: float; risk_level: str; primary_hazard: str
    imd_bands: IMDBandsModel; confidence: ConfidenceModel
    risk_trend: RiskTrendModel; exclusion: ExclusionModel
    # v4
    trend: str; trend_velocity: float; slope: float; r_squared: float
    anomaly_flag: bool; anomaly_severity: str
    anomaly_details: list[str]; max_z_score: float
    predicted_risk_score: float; predicted_risk_level: str
    risk_category_reason: str; decision_explanation: str
    # payout
    payout_triggered: bool; tier_label: str; tier_desc: str
    payout_percentage: float; coverage_cap: float
    gross_payout: float; platform_fee: float; net_payout: float
    risk_loading: float; claim_adjustment: float; final_payout: float
    effective_payout: float; payout: float
    payout_message: str; payout_explanation: str
    exclusion_applied: bool; adjusted_net_payout: float
    actuarial: ActuarialModel; fraud_check: FraudCheckModel
    timestamp: str


SimulateResponse = RiskResponse


class CalculateResponse(BaseModel):
    rainfall: float; aqi: float; wind_speed: float
    risk_score: float; risk_level: str; primary_hazard: str
    imd_bands: IMDBandsModel; confidence: ConfidenceModel
    risk_trend: RiskTrendModel
    # v4
    trend: str; trend_velocity: float
    anomaly_flag: bool; anomaly_severity: str
    predicted_risk_score: float; predicted_risk_level: str
    risk_category_reason: str; decision_explanation: str
    # payout
    payout_triggered: bool; tier_label: str
    payout_percentage: float; coverage_cap: float
    gross_payout: float; platform_fee: float; net_payout: float
    risk_loading: float; claim_adjustment: float; final_payout: float
    payout: float
    exclusion: ExclusionModel; fraud_check: FraudCheckModel
    actuarial: ActuarialModel
    payout_explanation: str; message: str