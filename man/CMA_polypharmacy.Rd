% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/polypharmacy.R
\name{CMA_polypharmacy}
\alias{CMA_polypharmacy}
\title{CMA constructor for polypharmacy.}
\usage{
CMA_polypharmacy(
  data = data,
  medication.groups = medication.class.colname,
  CMA.to.apply = NA,
  aggregate.first = TRUE,
  aggregation.method = NA,
  aggregation.method.arguments = NA,
  thresholds = NA,
  ID.colname = NA,
  event.date.colname = NA,
  event.duration.colname = NA,
  event.daily.dose.colname = NA,
  medication.class.colname = NA,
  carry.only.for.same.medication = NA,
  consider.dosage.change = NA,
  followup.window.start = 0,
  followup.window.start.unit = c("days", "weeks", "months", "years")[1],
  followup.window.duration = 365 * 2,
  followup.window.duration.unit = c("days", "weeks", "months", "years")[1],
  observation.window.start = 0,
  observation.window.start.unit = c("days", "weeks", "months", "years")[1],
  observation.window.duration = 365 * 2,
  observation.window.duration.unit = c("days", "weeks", "months", "years")[1],
  date.format = "\%m/\%d/\%Y",
  summary = "CMA for polypharmacy",
  force.NA.CMA.for.failed.patients = TRUE,
  parallel.backend = c("none", "multicore", "snow", "snow(SOCK)", "snow(MPI)",
    "snow(NWS)")[1],
  parallel.threads = "auto",
  suppress.warnings = FALSE,
  suppress.special.argument.checks = TRUE,
  ...
)
}
\arguments{
\item{data}{A \emph{\code{data.frame}} containing the events (prescribing or
dispensing) used to compute the CMA. Must contain, at a minimum, the patient
unique ID, the event date and duration, medication type, and might also contain the daily
dosage (the actual column names are defined in the
following four parameters).}

\item{medication.groups}{A \emph{string} with the name of the column containing the medication
groups. If multiple medication classes should belong to the same treatment group, they can be
differentiated here (important to investigate treatment switches)}

\item{CMA.to.apply}{A \emph{string} giving the name of the CMA function (1 to
9) that will be computed for each treatment group.}

\item{aggregate.first}{\emph{Logical}, if \code{TRUE}, aggregate across treatment groups before
summarizing over time during OW.}

\item{aggregation.method}{A \emph{string} giving the name of the function to
aggregate CMA values of medication group, or \code{NA} to return only raw CMA estimates
per medication group. Accepts summary functions such as "mean", "sd", "var", "min", "max",
and "median". Custom functions are possible as long as they take a numeric vector as input
and return a single numeric value.}

\item{aggregation.method.arguments}{optional, A \emph{named list} of additional arguments to the
function given in \code{aggregation method}, e.g. \code{na.rm = TRUE}.}

\item{thresholds}{optional, a \emph{number} to apply as threshold between aggregation and summarizing.}

\item{ID.colname}{A \emph{string}, the name of the column in
\code{data} containing the medication type. Defaults to
\code{medication.class.colname}.}

\item{event.date.colname}{A \emph{string}, the name of the column in
\code{data} containing the start date of the event (in the format given in
the \code{date.format} parameter); must be present.}

\item{event.duration.colname}{A \emph{string}, the name of the column in
\code{data} containing the event duration (in days); must be present.}

\item{event.daily.dose.colname}{A \emph{string}, the name of the column in
\code{data} containing the prescribed daily dose, or \code{NA} if not defined.}

\item{medication.class.colname}{A \emph{string}, the name of the column in
\code{data} containing the medication type, or \code{NA} if not defined.}

\item{carry.only.for.same.medication}{\emph{Logical}, if \code{TRUE}, the
carry-over applies only across medication of the same type; valid only for
CMAs 5 to 9, in which case it is coupled (i.e., the same value is used for
computing the treatment episodes and the CMA on each treatment episode).}

\item{consider.dosage.change}{\emph{Logical}, if \code{TRUE}, the carry-over
is adjusted to also reflect changes in dosage; valid only for CMAs 5 to 9, in
which case it is coupled (i.e., the same value is used for computing the
treatment episodes and the CMA on each treatment episode).}

\item{followup.window.start}{If a \emph{\code{Date}} object, it represents
the actual start date of the follow-up window; if a \emph{string} it is the
name of the column in \code{data} containing the start date of the follow-up
window either as the numbers of \code{followup.window.start.unit} units after
the first event (the column must be of type \code{numeric}) or as actual
dates (in which case the column must be of type \code{Date}); if a
\emph{number} it is the number of time units defined in the
\code{followup.window.start.unit} parameter after the begin of the
participant's first event; or \code{NA} if not defined.}

\item{followup.window.start.unit}{can be either \emph{"days"},
\emph{"weeks"}, \emph{"months"} or \emph{"years"}, and represents the time
units that \code{followup.window.start} refers to (when a number), or
\code{NA} if not defined.}

\item{followup.window.duration}{either a \emph{number} representing the
duration of the follow-up window in the time units given in
\code{followup.window.duration.unit}, or a \emph{string} giving the column
containing these numbers. Should represent a period for which relevant
medication events are recorded accurately (e.g. not extend after end of
relevant treatment, loss-to-follow-up or change to a health care provider
not covered by the database).}

\item{followup.window.duration.unit}{can be either \emph{"days"},
\emph{"weeks"}, \emph{"months"} or \emph{"years"}, and represents the time
units that \code{followup.window.duration} refers to, or \code{NA} if not
defined.}

\item{observation.window.start, observation.window.start.unit, observation.window.duration, observation.window.duration.unit}{the definition of the observation window
(see the follow-up window parameters above for details). Can be defined separately
for each patient and treatment group.}

\item{date.format}{A \emph{string} giving the format of the dates used in the
\code{data} and the other parameters; see the \code{format} parameters of the
\code{\link[base]{as.Date}} function for details (NB, this concerns only the
dates given as strings and not as \code{Date} objects).}

\item{summary}{Metadata as a \emph{string}, briefly describing this CMA.}

\item{force.NA.CMA.for.failed.patients}{\emph{Logical} describing how the
patients for which the CMA estimation fails are treated: if \code{TRUE}
they are returned with an \code{NA} CMA estimate, while for
\code{FALSE} they are omitted.}

\item{parallel.backend}{Can be "none" (the default) for single-threaded
execution, "multicore"  (using \code{mclapply} in package \code{parallel})
for multicore processing (NB. not currently implemented on MS Windows and
automatically falls back on "snow" on this platform),  or "snow",
"snow(SOCK)" (equivalent to "snow"), "snow(MPI)" or "snow(NWS)" specifying
various types of SNOW clusters (can be on the local machine or more complex
setups -- please see the documentation of package \code{snow} for details;
the last two require packages \code{Rmpi} and \code{nws}, respectively, not
automatically installed with \code{AdhereR}).}

\item{parallel.threads}{Can be "auto" (for \code{parallel.backend} ==
"multicore", defaults to the number of cores in the system as given by
\code{options("cores")}, while for \code{parallel.backend} == "snow",
defaults to 2), a strictly positive integer specifying the number of parallel
threads, or a more complex specification of the SNOW cluster nodes for
\code{parallel.backend} == "snow" (see the documentation of package
\code{snow} for details).}

\item{suppress.warnings}{\emph{Logical}, if \code{TRUE} don't show any
warnings.}

\item{suppress.special.argument.checks}{\emph{Logical} parameter for internal
use; if \code{FALSE} (default) check if the important columns in the \code{data}
have some of the reserved names, if \code{TRUE} this check is not performed.}

\item{...}{other possible parameters}
}
\value{
An \code{S3} object of class \code{CMA_polypharmacy} with the
following fields:
\itemize{
 \item \code{data} The actual event data, as given by the \code{data}
 parameter.
 \item \code{ID.colname} the name of the column in \code{data} containing the
 unique patient ID, as given by the \code{ID.colname} parameter.
 \item \code{event.date.colname} the name of the column in \code{data}
 containing the start date of the event (in the format given in the
 \code{date.format} parameter), as given by the \code{event.date.colname}
 parameter.
 \item \code{event.duration.colname} the name of the column in \code{data}
 containing the event duration (in days), as given by the
 \code{event.duration.colname} parameter.
 \item \code{event.daily.dose.colname} the name of the column in \code{data}
 containing the prescribed daily dose, as given by the
 \code{event.daily.dose.colname} parameter.
 \item \code{medication.class.colname} the name of the column in \code{data}
 containing the classes/types/groups of medication, as given by the
 \code{medication.class.colname} parameter.
 \item \code{carry.only.for.same.medication} whether the carry-over applies
 only across medication of the same type, as given by the
 \code{carry.only.for.same.medication} parameter.
 \item \code{consider.dosage.change} whether the carry-over is adjusted to
 reflect changes in dosage, as given by the \code{consider.dosage.change}
 parameter.
 \item \code{followup.window.start} the beginning of the follow-up window, as
 given by the \code{followup.window.start} parameter.
 \item \code{followup.window.start.unit} the time unit of the
 \code{followup.window.start}, as given by the
 \code{followup.window.start.unit} parameter.
 \item \code{followup.window.duration} the duration of the follow-up window,
 as given by the \code{followup.window.duration} parameter.
 \item \code{followup.window.duration.unit} the time unit of the
 \code{followup.window.duration}, as given by the
 \code{followup.window.duration.unit} parameter.
 \item \code{observation.window.start} the beginning of the observation
 window, as given by the \code{observation.window.start} parameter.
 \item \code{observation.window.start.unit} the time unit of the
 \code{observation.window.start}, as given by the
 \code{observation.window.start.unit} parameter.
 \item \code{observation.window.duration} the duration of the observation
 window, as given by the \code{observation.window.duration} parameter.
 \item \code{observation.window.duration.unit} the time unit of the
 \code{observation.window.duration}, as given by the
 \code{observation.window.duration.unit} parameter.
 \item \code{date.format} the format of the dates, as given by the
 \code{date.format} parameter.
 \item \code{summary} the metadata, as given by the \code{summary} parameter.
 \item \code{event.info} the \code{data.frame} containing the event info
 (irrelevant for most users; see \code{\link{compute.event.int.gaps}} for
 details).
 \item \code{aggregation.method} the aggregation method to combine CMA values
 from different groups.
 \item \code{computed.CMA} the class name of the computed CMA.
 \item \code{medication.groups} a \code{data.frame} with medication groups and
 classes
 \item \code{CMA} the \code{data.frame} containing the actual \code{CMA}
 estimates for each participant (the \code{ID.colname} column) and
 sometimes treatment group, with columns:
   \itemize{
     \item \code{ID.colname} the patient ID as given by the \code{ID.colname}
     parameter.
     \item \code{medication.groups} only when no aggregation method is used
     (\code{aggregation.method = NA}); the treatment group as given by the
     \code{medication.groups} parameter.
     \item \code{CMA} the treatment episode's estimated CMA.
   }
}
}
\description{
Constructs a CMA (continuous multiple-interval measures of medication
availability/gaps) object for polypharmacy.
}
\examples{
\dontrun{
CMA_PP <- CMA_polypharmacy(data = med.events.pp,
medication.groups = med.groups,
CMA.to.apply = "CMA7",
aggregate.first = TRUE, # aggregate before summarizing
aggregation.method = "mean", # compute mean of CMAs
aggregation.method.arguments = list(na.rm = TRUE), # remove NA's during calculation
thresholds = NA, # don't apply threshold
ID.colname="PATIENT_ID",
event.date.colname="DATE",
event.duration.colname="DURATION",
event.daily.dose.colname="PERDAY",
medication.class.colname="CATEGORY",
followup.window.start=0,
observation.window.start=180,
observation.window.duration=365,
carry.only.for.same.medication = TRUE);}
}
