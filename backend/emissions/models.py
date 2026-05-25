import uuid
from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    """
    Implements multi-tenancy. Every piece of ingested data, batch metadata,
    and audit log belongs strictly to an Organization to ensure strict multi-tenant isolation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DataBatch(models.Model):
    """
    Tracks the source of truth for an entire ingestion event.
    Stores metadata regarding *how* the data entered the system, preventing data lineage loss.
    """
    SOURCE_CHOICES = [
        ('SAP', 'SAP Procurement & Fuel Export (CSV)'),
        ('UTILITY', 'Utility Portal Monthly Export (CSV)'),
        ('CONCUR', 'Concur Corporate Travel API Sync (JSON)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="batches")
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    
    # Metadata for who uploaded/synced it and when
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Optional field to track the raw baseline name or identifier
    batch_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "Data Batches"

    def __str__(self):
        return f"{self.source_type} Batch ({self.id.hex[:8]}) - {self.uploaded_at.strftime('%Y-%m-%d')}"


class EmissionRecord(models.Model):
    """
    The normalized operational ledger. 
    Maintains a robust state machine, holding the original payload intact alongside 
    the normalized physical values and calculated emissions.
    """
    SCOPE_CHOICES = [
        ('1', 'Scope 1 (Direct Emissions)'),
        ('2', 'Scope 2 (Indirect - Purchased Electricity)'),
        ('3', 'Scope 3 (Value Chain / Travel / Procurement)'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Analyst Review'),
        ('SUSPICIOUS', 'Flagged Suspicious'),
        ('APPROVED', 'Approved & Locked for Audit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DataBatch, on_delete=models.CASCADE, related_name="records")
    
    # ESG Categorization
    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100)  # e.g., "Stationary Combustion", "Business Travel - Flight"

    # Lineage: Trace back to the exact source row index or object index in the upload file
    source_row_index = models.IntegerField(help_text="Line or object index from the original dataset")
    raw_data_payload = models.JSONField(help_text="Immutable snapshot of the original input data structure")

    # Ingested Input Data Metrics
    original_value = models.DecimalField(max_digits=15, decimal_places=4)
    original_unit = models.CharField(max_length=30)  # e.g., "Liters", "kWh", "Stück", "DEL->BOM"

    # Normalized Metrics (Standardized for processing engine conversions)
    normalized_value_kwh = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True, help_text="Normalized energy equivalent if applicable")
    
    # Final Calculated Carbon Value
    co2e_kg = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True, help_text="Calculated greenhouse gas impact")

    # Validation Engine State Machine
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    validation_flags = models.JSONField(default=list, blank=True, help_text="List of automation warning strings if data looks odd")

    # Audit Controls
    is_locked = models.BooleanField(default=False, help_text="Once true, records are read-only and sealed for auditors")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_records")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Record {self.id.hex[:8]} - Scope {self.scope} [{self.status}]"


class AuditLog(models.Model):
    """
    Maintains a tamper-proof, sequential log of all manual changes made to an 
    EmissionRecord by compliance analysts prior to finalized sign-off.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name="audit_trail")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    changed_field = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, help_text="Optional correction context provided by the analyst")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Edit on {self.record.id.hex[:8]} by {self.user.username if self.user else 'System'} at {self.timestamp}"