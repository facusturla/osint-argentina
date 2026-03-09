import re

def validate_cuit(cuit: str) -> bool:
    """
    Valida un número de CUIT/CUIL argentino.
    El cálculo usa el dígito verificador.
    """
    # Remove any non-numeric characters (dashes, spaces)
    cuit = re.sub(r'\D', '', cuit)
    
    if len(cuit) != 11:
        return False
        
    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    
    cuit_digits = [int(digit) for digit in cuit]
    
    # Calculate sum of products
    total = sum([base[i] * cuit_digits[i] for i in range(10)])
    
    remainder = total % 11
    verifier = 11 - remainder
    
    if verifier == 11:
        verifier = 0
    elif verifier == 10:
        verifier = 9 # Valid for CUILs starting with 23 or 33, simplified
        
    return verifier == cuit_digits[10]

def analyze_cuit(cuit: str) -> dict:
    """
    Returns a dictionary with basic information about the CUIT/CUIL
    if it is mathematically valid.
    """
    cuit = re.sub(r'\D', '', cuit)
    
    if not validate_cuit(cuit):
        return {"valid": False, "error": "CUIT/CUIL inválido según dígito verificador."}
        
    prefix = cuit[:2]
    # General logic for prefixes:
    # 20 - Hombre
    # 23, 24 - Hombre o Mujer
    # 27 - Mujer
    # 30, 33, 34 - Empresas / Sociedades
    
    tipo_persona = "Desconocido"
    if prefix in ['20', '23', '24', '27']:
        tipo_persona = "Persona Física"
    elif prefix in ['30', '33', '34']:
        tipo_persona = "Persona Jurídica (Empresa)"

    genero = "No aplica"
    if prefix == '20':
        genero = "Masculino"
    elif prefix == '27':
        genero = "Femenino"
        
    return {
        "valid": True,
        "formatted": f"{cuit[:2]}-{cuit[2:10]}-{cuit[10:]}",
        "raw": cuit,
        "tipo_persona": tipo_persona,
        "genero_inf": genero
    }
