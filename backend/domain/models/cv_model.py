from pydantic import BaseModel, ConfigDict, Field


class CVParsedProfile(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True)

	professional_summary: str = Field(description="Sintesi del profilo ricavata dal CV.")
	technical_skills: list[str] = Field(description="Competenze tecniche esplicitamente presenti nel CV.")
	relevant_experience: list[str] = Field(description="Esperienze e progetti rilevanti, senza inventare dettagli.")
	education: list[str] = Field(description="Formazione esplicitamente presente nel CV.")
	certifications: list[str] = Field(description="Certificazioni esplicitamente presenti nel CV.")
	interview_focus: list[str] = Field(description="Aree del CV utili per un colloquio sulla posizione scelta.")


class CVInterviewContext(BaseModel):
	model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

	selected_position: str = Field(min_length=1)
	profile: CVParsedProfile
