# coding=utf-8
from django.conf import settings
from django.db import models
from django.utils import dateformat
from django.utils import formats


class CommonBaseModel(models.Model):
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta(object):
        abstract = True


class Company(CommonBaseModel):
    """ Is the enterprise (organization) """
    name = models.CharField("Nome", max_length=256)

    organization_external = models.PositiveIntegerField(u"Organização (ID)")
    estimated_hours_external = models.PositiveIntegerField("Horas estimadas (ID)",
                                                           default=settings.COMPANY_ESTIMATED_HOURS_ID)
    spent_hours_external = models.PositiveIntegerField("Horas gastas (ID)",
                                                       default=settings.COMPANY_SPENT_HOURS_ID)

    class Meta(object):
        verbose_name = "Empresa"
        verbose_name_plural = verbose_name + "s"

    def __unicode__(self):
        return self.name


class Contract(CommonBaseModel):
    """ Company contract """
    company = models.ForeignKey(Company, verbose_name=Company._meta.verbose_name)

    name = models.CharField(u"Título", max_length=256)

    hours = models.PositiveIntegerField("Total de horas", help_text="Total de horas contratadas.")

    archive = models.BooleanField("Arquivar", default=False, help_text=u"Define se o contrato foi cancelado.")

    @property
    def average_hours(self):
        try:
            average = self.hours / self.period_set.count()
        except ZeroDivisionError:
            average = 0.0
        return average

    class Meta(object):
        verbose_name = "Contrato"
        verbose_name_plural = verbose_name + "s"

    def __unicode__(self):
        return self.name


class Period(CommonBaseModel):
    """ Contract expiration dates """
    dt_start = models.DateField(u'Início')
    dt_end = models.DateField(u'Término')

    contract = models.ForeignKey(Contract)

    class Meta(object):
        verbose_name = "Data"
        verbose_name_plural = verbose_name + "s"
        ordering = ('dt_start',)

    def __unicode__(self):
        date_format = formats.get_format("DATE_FORMAT", lang=settings.LANGUAGE_CODE)
        return u"{0:s} até {1:s}".format(dateformat.format(self.dt_start, date_format),
                                         dateformat.format(self.dt_end, date_format))