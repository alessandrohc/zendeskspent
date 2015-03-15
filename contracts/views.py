# coding=utf-8
from django.core.context_processors import csrf
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View

import forms
import models
import remotesyc.models
import utils
import copy


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
        response = HttpResponse('OK', content_type='text/' + subtype)
        response['Content-Disposition'] = 'attachment; filename="{0}"'.format('file.' + subtype)
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
                        context.update(self.make_context(request, contract, periods))
            else:
                context['related_form'] = forms.ContractForm(params={
                    'contracts': company.contract_set.filter(archive=False)
                })

        if '_export_as' in request.POST and request.POST['_export_as']:
            return self.export_as(request, context, request.POST['_export_as'])

        return render(request, "contracts/contracts.html", context)

    @staticmethod
    def make_context(request, contract, periods):
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