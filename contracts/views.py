from django.core.context_processors import csrf
from django.shortcuts import render
from django.views.generic import View
from django.core import serializers

import forms
import models
import remotesyc.models


class ContractView(View):
    def get(self, request, *args, **kwargs):
        return render(request, "contracts/contracts.html", {
            'form': forms.CompanyForm(),
            'form_step': 1
        })

    def post(self, request, *args, **kwargs):
        params = {
            'form': forms.CompanyForm(request.POST),
            'form_step': 1
        }
        params.update(csrf(request))

        if params['form'].is_valid():
            company = models.Company.objects.get(pk=request.POST['name'])

            params['form_step'] = 2

            if int(request.POST['form_step']) == params['form_step']:
                params['related_form'] = forms.ContractForm(request.POST, params={
                    'contracts': company.contract_set
                })

                if params['related_form'].is_valid():
                    contract = models.Contract.objects.get(pk=request.POST['contracts'])

                    params['period_form'] = forms.PeriodForm(request.POST, params={
                        'period': contract.period_set,
                    })

                    if params['period_form'].is_valid():
                        params['data'] = self.do_filter(contract, params['period_form'].cleaned_data['period'])
                        params['contract'] = contract
            else:
                params['related_form'] = forms.ContractForm(params={
                    'contracts': company.contract_set
                })
        return render(request, "contracts/contracts.html", params)

    def do_filter(self, contract, periods):
        tickets = remotesyc.models.Ticket.objects.filter(view_id=contract.company.view_external)
        related = {}
        for period in periods:
            related[period] = tickets.filter(created_at__gte=period.dt_start,
                                             created_at__lt=period.dt_end)
        if not related:
            related['all'] = tickets
        return related