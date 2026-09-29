# Existing Solutions Review

This document will record existing software and open-source research before we implement equivalent functionality.

## Initial findings

### Cash-flow forecasting
Commercial products already provide:
- cash-flow forecasting;
- AR/AP integration;
- scenario analysis;
- payment prediction;
- forecasting dashboards.

Therefore the project will not claim that cash-flow forecasting itself is novel.

### Proposed gap to investigate

The working gap is **independent forecast validation and reliability assessment**:

- Is the source data fit for forecasting?
- How accurate is the forecast historically for this specific business?
- Is the forecast systematically biased?
- At what horizon does forecast quality deteriorate?
- Under what business conditions does the forecast fail?
- Which model or baseline should this business actually trust?

This gap remains a research hypothesis until the project review is complete.

## Reference project

`arthurflor23/invoice-payment-prediction`

The repository demonstrates a multi-stage approach to invoice-payment prediction using classification and regression. It is a valuable reference for customer-payment features, model evaluation and research workflow.

We will use it as a reference, not as a template to clone.
