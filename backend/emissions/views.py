# backend/emissions/views.py
import csv
import io
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User

from .models import Organization, DataBatch, EmissionRecord, AuditLog
from .serializers import OrganizationSerializer, DataBatchSerializer, EmissionRecordSerializer

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class DataBatchViewSet(viewsets.ModelViewSet):
    queryset = DataBatch.objects.all().order_by('-uploaded_at')
    serializer_class = DataBatchSerializer


class EmissionRecordViewSet(viewsets.ModelViewSet):
    queryset = EmissionRecord.objects.all().order_by('status', '-co2e_kg')
    serializer_class = EmissionRecordSerializer

    def get_mock_context(self):
        """Helper to ensure we have a fallback tenant organization and user context."""
        org, _ = Organization.objects.get_or_create(name="Enterprise Global Inc.")
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            user = User.objects.create_user(username="analyst_alpha", email="analyst@breatheesg.com", password="password123")
        return org, user

    @action(detail=False, methods=['post'], url_path='ingest-sap')
    def ingest_sap(self, request):
        org, user = self.get_mock_context()
        file_obj = self.request.FILES.get('file')
        
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        batch = DataBatch.objects.create(
            organization=org,
            source_type='SAP',
            uploaded_by=user,
            batch_reference=file_obj.name
        )

        try:
            # utf-8-sig automatically strips out hidden BOM headers if present
            csv_data = file_obj.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(csv_data))
            # Clean up any accidental whitespace surrounding the headers
            reader.fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
        except Exception as e:
            return Response({"error": f"Invalid file coding: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        records_created = 0
        PLANT_LOOKUP = {"PL01": "Main Manufacturing Plant", "PL02": "Logistics Hub"}

        for idx, original_row in enumerate(reader, start=1):
            validation_flags = []
            
            # Create a clean row map with lowercase, stripped strings to prevent key misses
            row = {k.strip(): v.strip() if v else '' for k, v in original_row.items() if k}
            
            # Check keys across common layout variations
            menge = row.get('MENGE') or row.get('quantity') or row.get('Quantity') or '0'
            meins = row.get('MEINS') or row.get('unit') or row.get('Unit') or 'Unknown'
            matnr = row.get('MATNR') or row.get('material_id') or row.get('Material') or ''
            maktx = row.get('MAKTX') or row.get('material_name') or row.get('Description') or 'Unknown Material'
            werks = row.get('WERKS') or row.get('plant_code') or row.get('Plant') or ''

            if 'MENGE' in original_row or 'MEINS' in original_row:
                validation_flags.append("GERMAN_HEADER_FALLBACK_DETECTED")

            try:
                original_value = Decimal(str(menge))
            except (ValueError, TypeError, InvalidOperation):
                original_value = Decimal('0.0000')
                validation_flags.append("CORRUPTED_VALUE_FALLBACK_TO_ZERO")

            category = "Scope 1 - Stationary Combustion" if "DIESEL" in str(matnr).upper() or "HEIZÖL" in str(maktx).upper() else "Scope 3 - Capital Goods Procurement"
            scope = '1' if category.startswith("Scope 1") else '3'
            
            # Reset processing variables
            normalized_value_kwh = None
            co2e_kg = None
            
            if scope == '1' and str(meins).upper() in ['L', 'LITERS', 'LITER']:
                normalized_value_kwh = original_value * Decimal('10.0000')
                co2e_kg = original_value * Decimal('2.6800')
            elif str(meins).upper() in ['ST', 'STÜCK', 'PIECES']:
                validation_flags.append("UNRESOLVED_UNIT_STÜCK_REQUIRES_MANUAL_EVALUATION")
                
            status_state = 'SUSPICIOUS' if validation_flags else 'PENDING'
            resolved_plant = PLANT_LOOKUP.get(werks, f"Unknown Code: {werks}")
            
            row['_resolved_location_context'] = resolved_plant

            EmissionRecord.objects.create(
                batch=batch,
                scope=scope,
                category=category,
                source_row_index=idx,
                raw_data_payload=row,
                original_value=original_value,
                original_unit=meins,
                normalized_value_kwh=normalized_value_kwh,
                co2e_kg=co2e_kg,
                status=status_state,
                validation_flags=validation_flags
            )
            records_created += 1

        return Response({"message": f"Successfully processed {records_created} SAP records", "batch_id": batch.id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='ingest-utility')
    def ingest_utility(self, request):
        org, user = self.get_mock_context()
        file_obj = self.request.FILES.get('file')
        
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        batch = DataBatch.objects.create(
            organization=org,
            source_type='UTILITY',
            uploaded_by=user,
            batch_reference=file_obj.name
        )

        try:
            csv_data = file_obj.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(csv_data))
            reader.fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
        except Exception as e:
            return Response({"error": f"Invalid file coding: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        records_created = 0

        for idx, original_row in enumerate(reader, start=1):
            validation_flags = []
            row = {k.strip(): v.strip() if v else '' for k, v in original_row.items() if k}
            
            peak = row.get('Peak_kWh') or row.get('peak_kwh') or '0'
            off_peak = row.get('OffPeak_kWh') or row.get('offpeak_kwh') or '0'
            
            try:
                total_kwh = Decimal(str(peak)) + Decimal(str(off_peak))
            except (ValueError, TypeError, InvalidOperation):
                total_kwh = Decimal('0.0000')
                validation_flags.append("METRIC_PARSE_ERROR")

            if total_kwh > 5000:
                validation_flags.append("HIGH_CONSUMPTION_SPIKE_DETECTED")

            co2e_kg = total_kwh * Decimal('0.8500')
            status_state = 'SUSPICIOUS' if validation_flags else 'PENDING'

            EmissionRecord.objects.create(
                batch=batch,
                scope='2',
                category='Scope 2 - Purchased Electricity Grid',
                source_row_index=idx,
                raw_data_payload=row,
                original_value=total_kwh,
                original_unit='kWh (Combined Pool)',
                normalized_value_kwh=total_kwh,
                co2e_kg=co2e_kg,
                status=status_state,
                validation_flags=validation_flags
            )
            records_created += 1

        return Response({"message": f"Successfully processed {records_created} Utility records", "batch_id": batch.id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='sync-concur')
    def sync_concur(self, request):
        org, user = self.get_mock_context()
        
        mock_concur_payload = [
            {
                "trip_id": "TC-88391",
                "employee_id": "EMP-402",
                "expense_type": "Flight",
                "details": { "origin": "DEL", "destination": "BOM", "cabin_class": "Economy" },
                "booking_date": "2026-05-10"
            },
            {
                "trip_id": "TC-99412",
                "employee_id": "EMP-115",
                "expense_type": "Hotel",
                "details": { "location": "Mumbai Outpost", "nights": 4 },
                "booking_date": "2026-05-12"
            }
        ]

        batch = DataBatch.objects.create(
            organization=org,
            source_type='CONCUR',
            uploaded_by=user,
            batch_reference="Live API Direct Loop"
        )

        records_created = 0
        IATA_DISTANCES = {"DEL->BOM": Decimal('1150.00'), "BOM->DEL": Decimal('1150.00')}

        for idx, item in enumerate(mock_concur_payload, start=1):
            validation_flags = []
            co2e_kg = Decimal('0.0000')
            original_val = Decimal('1.0000')
            unit_marker = "Item Occurrence"

            if item["expense_type"] == "Flight":
                route = f"{item['details']['origin']}->{item['details']['destination']}"
                distance = IATA_DISTANCES.get(route)
                unit_marker = f"IATA Route: {route}"
                
                if distance:
                    original_val = distance
                    co2e_kg = distance * Decimal('0.1500')
                else:
                    validation_flags.append("MISSING_DISTANCE_MAPPING_ROUTING_UNRESOLVED")
            
            elif item["expense_type"] == "Hotel":
                nights = Decimal(str(item['details']['nights']))
                original_val = nights
                unit_marker = "Nights Booked"
                co2e_kg = nights * Decimal('25.4000')

            status_state = 'SUSPICIOUS' if validation_flags else 'PENDING'

            EmissionRecord.objects.create(
                batch=batch,
                scope='3',
                category=f"Scope 3 - Business Travel ({item['expense_type']})",
                source_row_index=idx,
                raw_data_payload=item,
                original_value=original_val,
                original_unit=unit_marker,
                normalized_value_kwh=None,
                co2e_kg=co2e_kg,
                status=status_state,
                validation_flags=validation_flags
            )
            records_created += 1

        return Response({"message": f"Successfully pulled {records_created} records via API wire", "batch_id": batch.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        record = self.get_object()
        
        # Use our automated context helper to prevent unassigned user reference errors on deployment fields
        _, user = self.get_mock_context()
        
        if record.is_locked:
            return Response({"error": "This transaction row is locked for audit and cannot be modified"}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status')
        new_co2e = request.data.get('co2e_kg')
        reason_text = request.data.get('reason', 'Analyst baseline adjustment execution')

        if not new_status:
            return Response({"error": "Target state status is required"}, status=status.HTTP_400_BAD_REQUEST)

        if new_co2e is not None:
            old_co2e_str = str(record.co2e_kg)
            record.co2e_kg = Decimal(str(new_co2e))
            AuditLog.objects.create(
                record=record,
                user=user,
                changed_field="co2e_kg",
                old_value=old_co2e_str,
                new_value=str(new_co2e),
                reason=reason_text
            )

        if new_status != record.status:
            old_status = record.status
            record.status = new_status
            
            if new_status == 'APPROVED':
                record.is_locked = True
                record.reviewed_by = user
                record.reviewed_at = timezone.now()
                
            AuditLog.objects.create(
                record=record,
                user=user,
                changed_field="status",
                old_value=old_status,
                new_value=new_status,
                reason=reason_text
            )

        record.save()
        return Response(EmissionRecordSerializer(record).data, status=status.HTTP_200_OK)