"""Cliente NVIDIA controlado para el comité de KIKE-NNN."""

from dataclasses import dataclass
from time import monotonic

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from agents_kike_nnn.config import (
    ConfiguracionAgentes,
    cargar_configuracion,
)


@dataclass(frozen=True)
class ResultadoAgente:
    correcto: bool
    modelo_solicitado: str
    modelo_utilizado: str
    contenido: str
    duracion_segundos: float
    uso_respaldo: bool
    tipo_error: str | None = None
    detalle_error: str | None = None


class ClienteNvidia:
    """Ejecuta llamadas acotadas, trazables y sin reintentos ocultos."""

    def __init__(
        self,
        configuracion: ConfiguracionAgentes | None = None,
    ) -> None:
        self.configuracion = configuracion or cargar_configuracion()
        self._cliente = OpenAI(
            api_key=self.configuracion.api_key,
            base_url=self.configuracion.base_url,
            max_retries=0,
        )

    def _consultar(
        self,
        *,
        modelo: str,
        sistema: str,
        solicitud: str,
        timeout: float,
        max_tokens: int,
        temperatura: float,
    ) -> tuple[str, float]:
        inicio = monotonic()

        respuesta = self._cliente.with_options(
            timeout=timeout,
        ).chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": solicitud},
            ],
            temperature=temperatura,
            max_tokens=max_tokens,
        )

        duracion = monotonic() - inicio
        contenido = respuesta.choices[0].message.content or ""

        if not contenido.strip():
            raise RuntimeError("El modelo devolvió una respuesta vacía.")

        return contenido, duracion

    def consultar_arquitecto(
        self,
        *,
        sistema: str,
        solicitud: str,
        max_tokens: int = 2500,
    ) -> ResultadoAgente:
        modelo = self.configuracion.modelo_arquitecto
        inicio = monotonic()

        try:
            contenido, duracion = self._consultar(
                modelo=modelo,
                sistema=sistema,
                solicitud=solicitud,
                timeout=180.0,
                max_tokens=max_tokens,
                temperatura=0.1,
            )
            return ResultadoAgente(
                correcto=True,
                modelo_solicitado=modelo,
                modelo_utilizado=modelo,
                contenido=contenido,
                duracion_segundos=duracion,
                uso_respaldo=False,
            )
        except Exception as error:
            return self._resultado_error(
                modelo=modelo,
                inicio=inicio,
                error=error,
            )

    def consultar_programador(
        self,
        *,
        sistema: str,
        solicitud: str,
        preferir_pro: bool = False,
        max_tokens: int = 3000,
    ) -> ResultadoAgente:
        pro = self.configuracion.modelo_programador
        flash = self.configuracion.modelo_programador_respaldo
        principal = pro if preferir_pro else flash
        respaldo = flash if preferir_pro else None
        inicio_total = monotonic()

        try:
            contenido, duracion = self._consultar(
                modelo=principal,
                sistema=sistema,
                solicitud=solicitud,
                timeout=90.0 if principal == flash else 120.0,
                max_tokens=max_tokens,
                temperatura=0.1,
            )
            return ResultadoAgente(
                correcto=True,
                modelo_solicitado=principal,
                modelo_utilizado=principal,
                contenido=contenido,
                duracion_segundos=duracion,
                uso_respaldo=False,
            )
        except (
            APITimeoutError,
            APIConnectionError,
            RateLimitError,
        ) as error_principal:
            if respaldo is None:
                return self._resultado_error(
                    modelo=principal,
                    inicio=inicio_total,
                    error=error_principal,
                )

            try:
                contenido, _ = self._consultar(
                    modelo=respaldo,
                    sistema=sistema,
                    solicitud=solicitud,
                    timeout=90.0,
                    max_tokens=max_tokens,
                    temperatura=0.1,
                )
                return ResultadoAgente(
                    correcto=True,
                    modelo_solicitado=principal,
                    modelo_utilizado=respaldo,
                    contenido=contenido,
                    duracion_segundos=monotonic() - inicio_total,
                    uso_respaldo=True,
                    tipo_error=type(error_principal).__name__,
                    detalle_error="El modelo principal no respondió.",
                )
            except Exception as error_respaldo:
                return self._resultado_error(
                    modelo=principal,
                    inicio=inicio_total,
                    error=error_respaldo,
                )
        except Exception as error:
            return self._resultado_error(
                modelo=principal,
                inicio=inicio_total,
                error=error,
            )

    @staticmethod
    def _resultado_error(
        *,
        modelo: str,
        inicio: float,
        error: Exception,
    ) -> ResultadoAgente:
        if isinstance(error, AuthenticationError):
            detalle = "NVIDIA rechazó la autenticación."
        elif isinstance(error, APITimeoutError):
            detalle = "La solicitud excedió el tiempo permitido."
        elif isinstance(error, RateLimitError):
            detalle = "NVIDIA limitó temporalmente las solicitudes."
        elif isinstance(error, APIConnectionError):
            detalle = "No fue posible mantener conexión con NVIDIA."
        else:
            detalle = str(error)[:300]

        return ResultadoAgente(
            correcto=False,
            modelo_solicitado=modelo,
            modelo_utilizado=modelo,
            contenido="",
            duracion_segundos=monotonic() - inicio,
            uso_respaldo=False,
            tipo_error=type(error).__name__,
            detalle_error=detalle,
        )
