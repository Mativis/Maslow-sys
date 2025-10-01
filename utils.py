from datetime import datetime, timedelta
from models import Documento

def calcular_data_validade(tipo_validade, data_personalizada=None):
    if tipo_validade == 'indeterminado':
        return None
    elif tipo_validade == '3':
        return datetime.now().date() + timedelta(days=90)
    elif tipo_validade == '6':
        return datetime.now().date() + timedelta(days=180)
    elif tipo_validade == '12':
        return datetime.now().date() + timedelta(days=365)
    elif tipo_validade == 'personalizado' and data_personalizada:
        return data_personalizada
    return None

def get_documentos_vencidos():
    hoje = datetime.now().date()
    return Documento.query.filter(Documento.data_validade < hoje, Documento.tipo_validade != 'indeterminado').all()

def get_documentos_proximos_vencer():
    hoje = datetime.now().date()
    proximo_mes = hoje + timedelta(days=30)
    return Documento.query.filter(
        Documento.data_validade >= hoje,
        Documento.data_validade <= proximo_mes,
        Documento.tipo_validade != 'indeterminado'
    ).all()
