# Domain Research & Mock Data Dictionary

This document details the real-world research used to create realistic data schemas for this application.

## Source Data Profiles

### 1. SAP Procurement Data (Scope 1 & Scope 3)
* **Research Insight:** Enterprise SAP configurations often use default ABAP technical labels or language-specific export tables rather than friendly English names.
* **Handled Reality:** * `BUKRS` (Company Code), `WERKS` (Plant/Facility Code), `MATNR` (Material ID), `MAKTX` (Material Name/Description), `MENGE` (Quantity), `MEINS` (Unit of Measure).
* **Sample Data Payload Example:**
  ```csv
  BUKRS,WERKS,MATNR,MAKTX,MENGE,MEINS,BUDAT
  1000,PL01,DIESEL01,Heizöl (Diesel),5000,L,20260515
  1000,PL02,STEEL05,Structural Steel,12.5,ST,20260516