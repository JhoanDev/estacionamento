from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from users.api.serializers import (
    CustomerSerializer,
    ParkingLotSerializer,
    ParkingSessionSerializer,
    UserProfileExampleSerializer,
    VehicleSerializer,
)
from users.models import Customer, ParkingLot, ParkingSession, UserProfileExample, Vehicle


class UserProfileExampleViewSet(ModelViewSet):
    serializer_class = UserProfileExampleSerializer
    permission_classes = [AllowAny]
    queryset = UserProfileExample.objects.all()
    http_method_names = ["get", "put"]


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all().order_by("name")
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]


class VehicleViewSet(ModelViewSet):
    queryset = Vehicle.objects.select_related("customer").all().order_by("plate")
    serializer_class = VehicleSerializer
    permission_classes = [AllowAny]


class ParkingLotViewSet(ModelViewSet):
    queryset = ParkingLot.objects.all().order_by("name")
    serializer_class = ParkingLotSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"])
    def occupancy(self, request, pk=None):
        parking_lot = self.get_object()
        return Response(self.get_serializer(parking_lot).data)


class ParkingSessionViewSet(ModelViewSet):
    queryset = ParkingSession.objects.select_related(
        "vehicle", "parking_lot"
    ).all()
    serializer_class = ParkingSessionSerializer
    permission_classes = [AllowAny]
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        with transaction.atomic():
            queryset = self.filter_queryset(
                self.get_queryset().select_for_update()
            )
            parking_session = get_object_or_404(queryset, pk=pk)
            self.check_object_permissions(request, parking_session)
            if not parking_session.is_active:
                raise serializers.ValidationError(
                    {"detail": "Este veículo já teve a saída registrada."}
                )

            updated = ParkingLot.objects.filter(
                pk=parking_session.parking_lot_id,
                occupied_spaces__gt=0,
            ).update(occupied_spaces=F("occupied_spaces") - 1)
            if not updated:
                raise serializers.ValidationError(
                    {"detail": "A ocupação do estacionamento está inconsistente."}
                )

            parking_session.exit_at = timezone.now()
            parking_session.save(update_fields=["exit_at"])

        return Response(self.get_serializer(parking_session).data, status=HTTP_200_OK)
