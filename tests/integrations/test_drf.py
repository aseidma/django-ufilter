import mock
import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import QueryDict
from rest_framework.exceptions import ValidationError

from django_ufilter.filtersets import FilterSet, ModelFilterSet
from django_ufilter.integrations.drf import DRFFilterBackend
from test_project.one_to_one.api import PlaceFilterSet
from test_project.one_to_one.models import Place, Restaurant


class TestDjangoFilterBackend(object):
    def test_get_filter_class_supplied(self):
        class View(object):
            filter_class = PlaceFilterSet

        filter_class = DRFFilterBackend().get_filter_class(View(), Place.objects.all())

        assert filter_class is PlaceFilterSet

    def test_get_filter_class_by_filter_fields(self):
        class View(object):
            filter_fields = ["name"]

        filter_class = DRFFilterBackend().get_filter_class(View(), Place.objects.all())

        assert issubclass(filter_class, ModelFilterSet)
        assert filter_class.Meta.model is Place
        assert filter_class.Meta.fields == ["name"]

    def test_get_filter_class_all_fields(self):
        class View(object):
            filter_fields = "__all__"

        filter_class = DRFFilterBackend().get_filter_class(View(), Place.objects.all())

        assert issubclass(filter_class, ModelFilterSet)
        assert filter_class.Meta.model is Place
        assert set(filter_class().filters.keys()) == {
            "restaurant",
            "id",
            "name",
            "address",
        }

    def test_get_filter_context(self):
        context = DRFFilterBackend().get_filter_context(request="request", view="view")

        assert context == {"request": "request", "view": "view"}

    def test_get_filter_queryset_not_filtered(self):
        assert DRFFilterBackend().filter_queryset(None, None, None) is None

    @mock.patch.object(FilterSet, "filter")
    def test_get_filter_queryset(self, mock_filter, db, rf):
        class View(object):
            filter_fields = ["name"]

        request = rf.get("/")
        request.query_params = QueryDict()

        filtered = DRFFilterBackend().filter_queryset(
            request=request, queryset=Place.objects.all(), view=View()
        )

        assert filtered == mock_filter.return_value

    @mock.patch.object(FilterSet, "filter")
    def test_get_filter_queryset_invalid_query(self, mock_filter, db, rf):
        mock_filter.side_effect = DjangoValidationError({"foo": "bar"})

        class View(object):
            filter_fields = ["name"]

        request = rf.get("/")
        request.query_params = QueryDict()

        with pytest.raises(ValidationError) as e:
            DRFFilterBackend().filter_queryset(
                request=request, queryset=Place.objects.all(), view=View()
            )

        assert e.value.detail == {"foo": ["bar"]}

    @mock.patch.object(FilterSet, "filter")
    def test_filter_queryset_supplied_model_mismatch(self, mock_filter, db, rf):
        class View(object):
            filter_class = PlaceFilterSet
            filter_fields = ["name"]

        request = rf.get("/")
        request.query_params = QueryDict()

        with pytest.raises(AssertionError):
            DRFFilterBackend().filter_queryset(
                request=request, queryset=Restaurant.objects.all(), view=View()
            )
