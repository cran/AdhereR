% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/adherer.R
\name{CMA_sliding_window}
\alias{CMA_sliding_window}
\title{CMA_sliding_window constructor.}
\usage{
CMA_sliding_window(
  CMA.to.apply,
  data,
  ID.colname = NA,
  event.date.colname = NA,
  event.duration.colname = NA,
  event.daily.dose.colname = NA,
  medication.class.colname = NA,
  medication.groups = NULL,
  flatten.medication.groups = FALSE,
  medication.groups.colname = ".MED_GROUP_ID",
  carry.only.for.same.medication = NA,
  consider.dosage.change = NA,
  followup.window.start = 0,
  followup.window.start.unit = c("days", "weeks", "months", "years")[1],
  followup.window.start.per.medication.group = FALSE,
  followup.window.duration = 365 * 2,
  followup.window.duration.unit = c("days", "weeks", "months", "years")[1],
  observation.window.start = 0,
  observation.window.start.unit = c("days", "weeks", "months", "years")[1],
  observation.window.duration = 365 * 2,
  observation.window.duration.unit = c("days", "weeks", "months", "years")[1],
  sliding.window.start = 0,
  sliding.window.start.unit = c("days", "weeks", "months", "years")[1],
  sliding.window.duration = 90,
  sliding.window.duration.unit = c("days", "weeks", "months", "years")[1],
  sliding.window.step.duration = 30,
  sliding.window.step.unit = c("days", "weeks", "months", "years")[1],
  sliding.window.no.steps = NA,
  return.inner.event.info = FALSE,
  date.format = "\%m/\%d/\%Y",
  summary = "CMA per sliding window",
  event.interval.colname = "event.interval",
  gap.days.colname = "gap.days",
  force.NA.CMA.for.failed.patients = TRUE,
  return.mapping.events.sliding.window = FALSE,
  parallel.backend = c("none", "multicore", "snow", "snow(SOCK)", "snow(MPI)",
    "snow(NWS)")[1],
  parallel.threads = "auto",
  suppress.warnings = FALSE,
  suppress.special.argument.checks = FALSE,
  ...
)
}
\arguments{
\item{CMA.to.apply}{A \emph{string} giving the name of the CMA function (1 to
9) that will be computed for each treatment episode.}

\item{data}{A \emph{\code{data.frame}} containing the events used to compute
the CMA. Must contain, at a minimum, the patient unique ID, the event date
and duration, and might also contain the daily dosage and medication type
(the actual column names are defined in the following four parameters).}

\item{ID.colname}{A \emph{string}, the name of the column in \code{data}
containing the unique patient ID; must be present.}

\item{event.date.colname}{A \emph{string}, the name of the column in
\code{data} containing the start date of the event (in the format given in
the \code{date.format} parameter); must be present.}

\item{event.duration.colname}{A \emph{string}, the name of the column in
\code{data} containing the event duration (in days); must be present.}

\item{event.daily.dose.colname}{A \emph{string}, the name of the column in
\code{data} containing the prescribed daily dose, or \code{NA} if not defined.}

\item{medication.class.colname}{A \emph{string}, the name of the column in
\code{data} containing the medication type, or \code{NA} if not defined.}

\item{medication.groups}{A \emph{vector} of characters defining medication
groups or the name of a column in \code{data} that defines such groups.
The names of the vector are the medication group unique names, while
the content defines them as logical expressions. While the names can be any
string of characters except "\}", it is recommended to stick to the rules for
defining vector names in \code{R}. For example,
\code{c("A"="CATEGORY == 'medA'", "AA"="{A} & PERDAY < 4"} defines two
medication groups: \emph{A} which selects all events of type "medA", and
\emph{B} which selects all events already defined by "A" but with a daily
dose lower than 4. If \code{NULL}, no medication groups are defined. If
medication groups are defined, there is one CMA estimate for each group;
moreover, there is a special group \emph{__ALL_OTHERS__} automatically defined
containing all observations \emph{not} covered by any of the explicitly defined
groups.}

\item{flatten.medication.groups}{\emph{Logical}, if \code{FALSE} (the default)
then the \code{CMA} and \code{event.info} components of the object are lists
with one medication group per element; otherwise, they are \code{data.frame}s
with an extra column containing the medication group (its name is given by
\code{medication.groups.colname}).}

\item{medication.groups.colname}{a \emph{string} (defaults to ".MED_GROUP_ID")
giving the name of the column storing the group name when
\code{flatten.medication.groups} is \code{TRUE}.}

\item{carry.only.for.same.medication}{\emph{Logical}, if \code{TRUE}, the
carry-over applies only across medication of the same type.}

\item{consider.dosage.change}{\emph{Logical}, if \code{TRUE}, the carry-over
is adjusted to also reflect changes in dosage.}

\item{followup.window.start}{If a \emph{\code{Date}} object, it represents
the actual start date of the follow-up window; if a \emph{string} it is the
name of the column in \code{data} containing the start date of the follow-up
window either as the numbers of \code{followup.window.start.unit} units after
the first event (the column must be of type \code{numeric}) or as actual
dates (in which case the column must be of type \code{Date} or a string
that conforms to the format specified in \code{date.format}); if a
\emph{number} it is the number of time units defined in the
\code{followup.window.start.unit} parameter after the begin of the
participant's first event; or \code{NA} if not defined.}

\item{followup.window.start.unit}{can be either \emph{"days"},
\emph{"weeks"}, \emph{"months"} or \emph{"years"}, and represents the time
units that \code{followup.window.start} refers to (when a number), or
\code{NA} if not defined.}

\item{followup.window.start.per.medication.group}{a \emph{logical}: if there are
medication groups defined and this is \code{TRUE}, then the first event
considered for the follow-up window start is relative to each medication group
separately, otherwise (the default) it is relative to the patient.}

\item{followup.window.duration}{either a \emph{number} representing the
duration of the follow-up window in the time units given in
\code{followup.window.duration.unit}, or a \emph{string} giving the column
containing these numbers. Should represent a period for which relevant
medication events are recorded accurately (e.g. not extend after end of
relevant treatment, loss-to-follow-up or change to a health care provider not
covered by the database).}

\item{followup.window.duration.unit}{can be either \emph{"days"},
\emph{"weeks"}, \emph{"months"} or \emph{"years"}, and represents the time
units that \code{followup.window.duration} refers to, or \code{NA} if not
defined.}

\item{observation.window.start, observation.window.start.unit, observation.window.duration, observation.window.duration.unit}{the definition of the observation window
(see the follow-up window parameters above for details).}

\item{sliding.window.start, sliding.window.start.unit, sliding.window.duration, sliding.window.duration.unit}{the definition of the first sliding window
(see the follow-up window parameters above for details).}

\item{sliding.window.step.duration, sliding.window.step.unit}{if not missing
(\code{NA}), these give the step (or "jump") to the right of the sliding
window in time units.}

\item{sliding.window.no.steps}{a \emph{integer} specifying the desired number
of sliding windows to cover the observation window (if possible); trumps
\code{sliding.window.step.duration} and \code{sliding.window.step.unit}.}

\item{return.inner.event.info}{\emph{Logical} specifying if the function
should also return the event.info for all the individual events in each
sliding window; by default it is \code{FALSE} as this information is useful
only in very specific cases (e.g., plotting the event intervals) and adds a
small but non-negligible computational overhead.}

\item{date.format}{A \emph{string} giving the format of the dates used in the
\code{data} and the other parameters; see the \code{format} parameters of the
\code{\link[base]{as.Date}} function for details (NB, this concerns only the
dates given as strings and not as \code{Date} objects).}

\item{summary}{Metadata as a \emph{string}, briefly describing this CMA.}

\item{event.interval.colname}{A \emph{string}, the name of a newly-created
column storing the number of days between the start of the current event and
the start of the next one; the default value "event.interval" should be
changed only if there is a naming conflict with a pre-existing
"event.interval" column in \code{event.info}.}

\item{gap.days.colname}{A \emph{string}, the name of a newly-created column
storing the number of days when medication was not available (i.e., the
"gap days"); the default value "gap.days" should be changed only if there is
a naming conflict with a pre-existing "gap.days" column in \code{event.info}.}

\item{force.NA.CMA.for.failed.patients}{\emph{Logical} describing how the
patients for which the CMA estimation fails are treated: if \code{TRUE}
they are returned with an \code{NA} CMA estimate, while for
\code{FALSE} they are omitted.}

\item{return.mapping.events.sliding.window}{A \emph{Logical}, if \code{TRUE} then
the mapping between events and sliding windows is returned as the component
\code{mapping.windows.to.events}, which is a \code{data.table} giving, for
each sliding window, the events that belong to it (an event is given by its row
number in the \code{data}).}

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
An \code{S3} object of class \code{CMA_sliding_window} with the
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
 reflect changes in dosage, as given by the \code{consider.dosage.change} parameter.
 \item \code{followup.window.start} the beginning of the follow-up window,
  as given by the \code{followup.window.start} parameter.
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
 \item \code{computed.CMA} the class name of the computed CMA.
 \item \code{CMA} the \code{data.frame} containing the actual \code{CMA}
 estimates for each participant (the \code{ID.colname} column) and sliding
 window, with columns:
   \itemize{
     \item \code{ID.colname} the patient ID as given by the \code{ID.colname}
     parameter.
     \item \code{window.ID} the unique window ID (within patients).
     \item \code{window.start} the window's start date (as a \code{Date}
     object).
     \item \code{window.end} the window's end date (as a \code{Date} object).
     \item \code{CMA} the window's estimated CMA.
   }
}
Please note that if \code{medication.groups} are defined, then the \code{CMA}
and \code{event.info} are named lists, each element containing the CMA and
event.info corresponding to a single medication group (the element's name).
}
\description{
Applies a given CMA to each sliding window and constructs a
CMA_sliding_window object.
}
\details{
\code{CMA_sliding_window} first computes a set of fixed-size (possibly partly
overlapping) sliding windows,
each sliding to the right by a fixed timelag,
and then, for each of them, it computes the given "simple" CMA.
Thus, as opposed to the "simple" CMAs 1 to 9, it returns a set of CMAs, with
possibly more than one element.

It is highly similar to \code{\link{CMA_per_episode}} which computes a CMA
for a set of treatment episodes.
}
\examples{
\dontrun{
cmaW <- CMA_sliding_window(CMA="CMA1",
                           data=med.events,
                           ID.colname="PATIENT_ID",
                           event.date.colname="DATE",
                           event.duration.colname="DURATION",
                           event.daily.dose.colname="PERDAY",
                           medication.class.colname="CATEGORY",
                           carry.only.for.same.medication=FALSE,
                           consider.dosage.change=FALSE,
                           followup.window.start=0,
                           observation.window.start=0,
                           observation.window.duration=365,
                           sliding.window.start=0,
                           sliding.window.start.unit="days",
                           sliding.window.duration=90,
                           sliding.window.duration.unit="days",
                           sliding.window.step.duration=7,
                           sliding.window.step.unit="days",
                           sliding.window.no.steps=NA,
                           date.format="\%m/\%d/\%Y"
                          );}
}
\seealso{
\code{\link{CMA_per_episode}} is very similar, computing a "simple"
CMA for each of the treatment episodes.
The "simple" CMAs that can be computed comprise \code{\link{CMA1}},
\code{\link{CMA2}}, \code{\link{CMA3}}, \code{\link{CMA4}},
\code{\link{CMA5}}, \code{\link{CMA6}}, \code{\link{CMA7}},
\code{\link{CMA8}}, \code{\link{CMA9}}, as well as user-defined classes
derived from \code{\link{CMA0}} that have a \code{CMA} component giving the
estimated CMA per patient as a \code{data.frame}.
If \code{return.mapping.events.sliding.window} is \code{TRUE}, then this also has an
attribute \code{mapping.windows.to.events} that gives the mapping between
episodes and events as a \code{data.table} with the following columns:
\itemize{
 \item \code{patid} the patient ID.
 \item \code{window.ID} the episode unique ID (increasing sequentially).
 \item \code{event.index.in.data} the event given by its row number in the \code{data}.
}
}
