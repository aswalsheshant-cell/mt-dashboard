/**
 * Sprint 8: Inventory & Supply Chain Engine
 * Calculates Days of Cover (DOC), OOS classification, Pre-Promo Sufficiency,
 * and Supply Chain Fill-Rate (CFR/OTIF) lost revenue.
 */
window.InventoryEngine = (function () {
  'use strict';

  const THRESHOLDS = {
    CRITICAL_OOS: 7,   // < 7 days
    LOW_COVER: 15,     // 7 - 14.9 days
    HEALTHY_MAX: 35,   // 15 - 35 days
    OVERSTOCK: 60      // > 60 days
  };

  function calculateDaysOfCover(sohUnits, avgDailyOfftakeUnits) {
    const dailyDemand = Math.max(0.1, Number(avgDailyOfftakeUnits) || 0.1);
    const soh = Math.max(0, Number(sohUnits) || 0);
    const doc = parseFloat((soh / dailyDemand).toFixed(1));

    let status = 'HEALTHY';
    let badgeClass = 'badge-success';
    let label = 'Healthy Cover';

    if (doc < THRESHOLDS.CRITICAL_OOS) {
      status = 'CRITICAL_OOS';
      badgeClass = 'badge-danger';
      label = 'Critical OOS Risk';
    } else if (doc < THRESHOLDS.LOW_COVER) {
      status = 'LOW_COVER';
      badgeClass = 'badge-warning';
      label = 'Low Stock Cover';
    } else if (doc > THRESHOLDS.OVERSTOCK) {
      status = 'OVERSTOCK_EXPIRY_RISK';
      badgeClass = 'badge-purple';
      label = 'Overstock / Expiry Risk';
    }

    return { doc, status, badgeClass, label };
  }

  function checkPromoStockSufficiency(params) {
    const baselineDaily = Math.max(0, Number(params.baselineDailyOfftake) || 0);
    const durationDays = Math.max(1, Number(params.promoDurationDays) || 14);
    const upliftMultiplier = 1 + (Math.max(0, Number(params.projectedUpliftPct) || 0) / 100);
    const currentSoh = Math.max(0, Number(params.currentSohUnits) || 0);

    const projectedDailyDemand = baselineDaily * upliftMultiplier;
    const totalPromoDemand = Math.round(projectedDailyDemand * durationDays);
    const isSufficient = currentSoh >= totalPromoDemand;
    const deficitUnits = isSufficient ? 0 : (totalPromoDemand - currentSoh);
    const bufferCoveragePct = totalPromoDemand > 0 ? parseFloat(((currentSoh / totalPromoDemand) * 100).toFixed(1)) : 100;

    return {
      projectedDailyDemand: parseFloat(projectedDailyDemand.toFixed(1)),
      totalPromoDemandUnits: totalPromoDemand,
      currentSohUnits: currentSoh,
      isSufficient,
      deficitUnits,
      bufferCoveragePct
    };
  }

  function calculateFillRateImpact(params) {
    const indent = Math.max(0, Number(params.orderedIndentUnits) || 0);
    const dispatched = Math.max(0, Number(params.dispatchedUnits) || 0);
    const onTime = Math.max(0, Number(params.onTimeOrders) || 0);
    const totalOrders = Math.max(1, Number(params.totalOrders) || 1);
    const asp = Math.max(0, Number(params.averageSellingPrice) || 0);

    const cfrPct = indent > 0 ? parseFloat(((dispatched / indent) * 100).toFixed(1)) : 100.0;
    const otifPct = parseFloat(((onTime / totalOrders) * 100).toFixed(1));
    const unfulfilledUnits = Math.max(0, indent - dispatched);
    const lostRevenueLacs = parseFloat(((unfulfilledUnits * asp) / 100000).toFixed(2));

    return {
      orderedIndentUnits: indent,
      dispatchedUnits: dispatched,
      unfulfilledUnits,
      cfrPct,
      otifPct,
      lostRevenueLacs
    };
  }

  return {
    calculateDaysOfCover,
    checkPromoStockSufficiency,
    calculateFillRateImpact
  };
})();
