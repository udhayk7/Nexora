"""SQLAlchemy models package."""

from app.models.analysis import ResumeAnalysis
from app.models.application import (
    ApplicationActivity,
    ApplicationInterview,
    ApplicationStatusHistory,
    JobApplication,
)
from app.models.assistant import (
    ApplicationEmail,
    ApplicationPreparation,
    CoverLetter,
    GmailConnection,
)
from app.models.base import Base
from app.models.company import Company, CompanySource, DiscoveryScanLog
from app.models.company_intelligence import (
    CompanyIntelligence,
    CompanyResearchReport,
    CompanyResearchSource,
)
from app.models.interview_prep import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewPreparationNote,
    InterviewPreparationSession,
    InterviewQuestion,
)
from app.models.job import Job, JobSource, JobVerification
from app.models.match import JobMatch, UserMatchingPreference
from app.models.notification import Notification, UserNotificationPreference
from app.models.recommendation import AIJobMatch, JobIntelligence
from app.models.resume import Resume, ResumeVersion
from app.models.tailoring import ResumeTailoringChange, ResumeTailoringSession
from app.models.token import RefreshToken
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "Resume",
    "ResumeVersion",
    "ResumeAnalysis",
    "Company",
    "CompanySource",
    "DiscoveryScanLog",
    "CompanyIntelligence",
    "CompanyResearchSource",
    "CompanyResearchReport",
    "Job",
    "JobSource",
    "JobVerification",
    "UserMatchingPreference",
    "JobMatch",
    "JobIntelligence",
    "AIJobMatch",
    "ResumeTailoringSession",
    "ResumeTailoringChange",
    "JobApplication",
    "ApplicationStatusHistory",
    "ApplicationActivity",
    "ApplicationInterview",
    "Notification",
    "UserNotificationPreference",
    "GmailConnection",
    "ApplicationPreparation",
    "CoverLetter",
    "ApplicationEmail",
    "InterviewPreparationSession",
    "InterviewQuestion",
    "InterviewAnswer",
    "InterviewEvaluation",
    "InterviewPreparationNote",
]
