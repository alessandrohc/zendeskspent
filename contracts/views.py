# coding=utf-8
from django.conf import settings

from django.core.context_processors import csrf
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View
import datetime

import forms
import models
import remotesyc.models
import utils
import copy
import csv
import StringIO


class ContractView(View):

    def get(self, request, *args, **kwargs):
        return render(request, "contracts/contracts.html", {
            'form': forms.CompanyForm(),
            'form_step': 1
        })

    @staticmethod
    def post_changed(request):
        _post = copy.deepcopy(request.POST)
        if 'status' not in _post:  # Force default
            _post['status'] = remotesyc.models.Ticket.STATUS.CLOSED
        return _post

    @staticmethod
    def export_as(request, context, subtype):
        def resolve_spent_hours(obj):
            return utils.float_number(obj.get_field_value(context['contract'].company.spent_hours_external))

        def resolve_estimated_hours(obj):
            return utils.float_number(obj.get_field_value(context['contract'].company.estimated_hours_external))

        stream = StringIO.StringIO()
        csv_writer = csv.writer(stream)
        csv_writer.writerow(settings.EXPORT_CSV_COLUMNS)
        names = ['subject', 'created_at', 'updated_at', 'resolve_spent_hours', 'resolve_estimated_hours']
        rows = []
        for queryset in context['intervals'].values():
            for item in queryset:
                row = []
                for name in names:
                    if hasattr(item, name):
                        row.append(getattr(item, name))
                    else:
                        row.append(locals()[name](item))
                rows.append(row)
        csv_writer.writerows(rows)

        response = HttpResponse(stream.getvalue(), content_type='text/' + subtype)
        filename = "{0:s}[{1!s}].{2:s}".format(context['contract'].company, datetime.date.today(), subtype)
        response['Content-Disposition'] = 'attachment; filename="{0:s}"'.format(filename)
        return response

    # noinspection DjangoOrm
    def post(self, request, *args, **kwargs):
        context = {
            'form': forms.CompanyForm(self.post_changed(request)),
            'form_step': 1
        }
        context.update(csrf(request))
        if context['form'].is_valid():
            company = models.Company.objects.get(pk=request.POST['name'])

            context['form_step'] = 2

            if int(request.POST['form_step']) == context['form_step']:
                context['related_form'] = forms.ContractForm(request.POST, params={
                    'contracts': company.contract_set.filter(archive=False)
                })

                if context['related_form'].is_valid():
                    contract = models.Contract.objects.get(pk=request.POST['contracts'])

                    context['period_form'] = forms.PeriodForm(request.POST, params={
                        'period': contract.period_set,
                    })

                    if context['period_form'].is_valid():
                        periods = context['period_form'].cleaned_data['period']
                        periods = periods if len(periods) > 0 else contract.period_set.all()
                        context.update(self.extra_context(request, contract, periods))
            else:
                context['related_form'] = forms.ContractForm(params={
                    'contracts': company.contract_set.filter(archive=False)
                })

        if '_export_as' in request.POST and request.POST['_export_as']:
            return self.export_as(request, context, request.POST['_export_as'])

        return render(request, "contracts/contracts.html", context)

    @staticmethod
    def extra_context(request, contract, periods):
        tickets = remotesyc.models.Ticket.objects.filter(organization_id=contract.company.organization_external)

        if not request.POST['status'] == remotesyc.models.Ticket.STATUS.ALL:
            tickets = tickets.filter(status=request.POST['status'])

        extra_context = {
            'contract': contract,
            'intervals': {}
        }
        for period in periods:
            extra_context['intervals'][period] = tickets.filter(updated_at__range=[period.dt_start, period.dt_end])

        # horas do total de tickets nos períodos selecionados
        extra_context['spent_hours'] = utils.calc_spent_hours(contract, extra_context['intervals'].values())

        if len(periods) == 1:
            spent_credits = utils.calc_spent_credits(contract, periods[0], request.POST['status'])

            # total de horas válidas
            extra_context['valid_hours'] = contract.average_hours + spent_credits

            # saldo devedor
            extra_context['spent_credits'] = spent_credits

            extra_context['remainder_hours'] = extra_context['valid_hours'] - extra_context['spent_hours']
        else:
            extra_context['remainder_hours'] = utils.calc_remainder_hours(contract, extra_context['spent_hours'])

        return extra_context