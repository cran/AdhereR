% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/adherer.R
\name{compute.treatment.episodes}
\alias{compute.treatment.episodes}
\title{Compute Treatment Episodes.}
\usage{
compute.treatment.episodes(
  data,
  ID.colname = NA,
  event.date.colname = NA,
  event.duration.colname = NA,
  event.daily.dose.colname = NA,
  medication.class.colname = NA,
  carryover.within.obs.window = TRUE,
  carry.only.for.same.medication = TRUE,
  consider.dosage.change = TRUE,
  medication.change.means.new.treatment.episode = TRUE,
  dosage.change.means.new.treatment.episode = FALSE,
  maximum.permissible.gap = 90,
  maximum.permissible.gap.unit = c("days", "weeks", "months", "years", "percent")[1],
  maximum.permissible.gap.append.to.episode = FALSE,
  followup.window.start = 0,
  followup.window.start.unit = c("days", "weeks", "months", "years")[1],
  followup.window.duration = 365 * 2,
  followup.window.duration.unit = c("days", "weeks", "months", "years")[1],
  event.interval.colname = "event.interval",
  gap.days.colname = "gap.days",
  return.mapping.events.episodes = FALSE,
  date.format = "\%m/\%d/\%Y",
  parallel.backend = c("none", "multicore", "snow", "snow(SOCK)", "snow(MPI)",
    "snow(NWS)")[1],
  parallel.threads = "auto",
  suppress.warnings = FALSE,
  suppress.special.argument.checks = FALSE,
  return.data.table = FALSE,
  ...
)
}
\arguments{
\item{data}{A \emph{\code{data.frame}} containing the events used to
compute the CMA. Must contain, at a minimum, the patient unique ID, the event
date and duration, and might also contain the daily dosage and medication
type (the actual column names are defined in the following four parameters);
the \code{CMA} constructors call this parameter \code{data}.}

\item{ID.colname}{A \emph{string}, the name of the column in \code{data}
containing the unique patient ID, or \code{NA} if not defined.}

\item{event.date.colname}{A \emph{string}, the name of the column in
\code{data} containing the start date of the event (in the format given in
the \code{date.format} parameter), or \code{NA} if not defined.}

\item{event.duration.colname}{A \emph{string}, the name of the column in
\code{data} containing the event duration (in days), or \code{NA} if not
defined.}

\item{event.daily.dose.colname}{A \emph{string}, the name of the column in
\code{data} containing the prescribed daily dose, or \code{NA} if not defined.}

\item{medication.class.colname}{A \emph{string}, the name of the column in
\code{data} containing the classes/types/groups of medication, or \code{NA}
if not defined.}

\item{carryover.within.obs.window}{\emph{Logical}, if \code{TRUE} consider
the carry-over within the observation window, or \code{NA} if not defined.}

\item{carry.only.for.same.medication}{\emph{Logical}, if \code{TRUE} the
carry-over applies only across medication of the same type, or \code{NA} if
not defined.}

\item{consider.dosage.change}{\emph{Logical}, if \code{TRUE} the carry-over
is adjusted to reflect changes in dosage, or \code{NA} if not defined.}

\item{medication.change.means.new.treatment.episode}{\emph{Logical}, should
a change in medication automatically start a new treatment episode?}

\item{dosage.change.means.new.treatment.episode}{\emph{Logical}, should
a change in dosage automatically start a new treatment episode?}

\item{maximum.permissible.gap}{The \emph{number} of units given by
\code{maximum.permissible.gap.unit} representing the maximum duration of
permissible gaps between treatment episodes (can also be a percent, see
\code{maximum.permissible.gap.unit} for details).}

\item{maximum.permissible.gap.unit}{can be either \emph{"days"},
\emph{"weeks"}, \emph{"months"}, \emph{"years"} or \emph{"percent"}, and
represents the time units that \code{maximum.permissible.gap} refers to;
if \emph{percent}, then  \code{maximum.permissible.gap} is interpreted as a
percent (can be greater than 100\%) of the duration of the current
prescription.}

\item{maximum.permissible.gap.append.to.episode}{a \emph{logical} value
specifying of the \code{maximum.permissible.gap} should be append at the
end of an episode with a gap larger than the \code{maximum.permissible.gap};
\code{FALSE} (the default) mean no addition, while \code{TRUE} mean that the
full \code{maximum.permissible.gap} is added.}

\item{followup.window.start}{If a \emph{\code{Date}} object it is the actual
start date of the follow-up window; if a \emph{string} it is the name of the
column in \code{data} containing the start date of the follow-up window; if a
\emph{number} it is the number of time units defined in the
\code{followup.window.start.unit} parameter after the begin of the
participant's first event; or \code{NA} if not defined.}

\item{followup.window.start.unit}{can be either \emph{"days"}, \emph{"weeks"},
\emph{"months"} or \emph{"years"}, and represents the time units that
\code{followup.window.start} refers to (when a number), or \code{NA} if not
defined.}

\item{followup.window.duration}{a \emph{number} representing the duration of
the follow-up window in the time units given in
\code{followup.window.duration.unit}, or \code{NA} if not defined.}

\item{followup.window.duration.unit}{can be either \emph{"days"},
\emph{"weeks"}, \emph{"months"} or \emph{"years"}, and represents the time
units that \code{followup.window.duration} refers to, or \code{NA} if not
defined.}

\item{event.interval.colname}{A \emph{string}, the name of a newly-created
column storing the number of days between the start of the current event and
the start of the next one; the default value "event.interval" should be
changed only if there is a naming conflict with a pre-existing
"event.interval" column in \code{event.info}.}

\item{gap.days.colname}{A \emph{string}, the name of a newly-created column
storing the number of days when medication was not available (i.e., the
"gap days"); the default value "gap.days" should be changed only if there is
a naming conflict with a pre-existing "gap.days" column in \code{event.info}.}

\item{return.mapping.events.episodes}{A \emph{Logical}, if \code{TRUE} then
the mapping between events and episodes is returned as the attribute
\code{mapping.episodes.to.events}, which is a \code{data.table} giving, for
each episode, the events that belong to it (an event is given by its row
number in the \code{data}). Please note that the episodes returned are quite
"generic" (e.g., they include all the events in the FUW), because which events
will be actually used in the computation of a \code{CMA_per_episode} depend on
which simple CMA is used (see also \code{CMA_per_episode}), and should be used
with care (we recommend using the mappings given by \code{CMA_per_episode}
instead).}

\item{date.format}{A \emph{string} giving the format of the dates used in the
\code{data} and the other parameters; see the \code{format} parameters of the
\code{\link[base]{as.Date}} function for details (NB, this concerns only the
dates given as strings and not as \code{Date} objects).}

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

\item{return.data.table}{\emph{Logical}, if \code{TRUE} return a
\code{data.table} object, otherwise a \code{data.frame}.}

\item{...}{extra arguments.}
}
\value{
A \code{data.frame} or \code{data.table} with the following columns
(or \code{NULL} if no
treatment episodes could be computed):
\itemize{
 \item \code{patid} the patient ID.
 \item \code{episode.ID} the episode unique ID (increasing sequentially).
 \item \code{episode.start} the episode start date.
 \item \code{end.episode.gap.days} the corresponding gap days of the last event in this episode.
 \item \code{episode.duration} the episode duration in days.
 \item \code{episode.end} the episode end date.
}
If \code{mapping.episodes.to.events} is \code{TRUE}, then this also has an
\emph{attribute} \code{mapping.episodes.to.events} that gives the mapping between
episodes and events as a \code{data.table} with the following columns:
\itemize{
 \item \code{patid} the patient ID.
 \item \code{episode.ID} the episode unique ID (increasing sequentially).
 \item \code{event.index.in.data} the event given by its row number in the \code{data}.
}
}
\description{
For a given event (prescribing or dispensing) database, compute the treatment
episodes for each patient in various scenarious.
}
\details{
This should in general not be called directly by the user, but is provided as
a basis for the extension to new CMAs.

For the last treatment episode, the gap is considered only when longer than
the maximum permissible gap.
Please note the following:
\itemize{
 \item episode starts at first medication event for a particular medication,
 \item episode ends on the day when the last supply of that medication
 finished or if a period longer than the permissible gap preceded the next
 medication event, or at the end of the FUW,
 \item end episode gap days represents either the number of days after the
 end of the treatment episode (if medication changed, or if a period longer
 than the permissible gap preceded the next medication event) or at the
 end of (and within) the episode, i.e. the number of days after the last
 supply finished (if no other medication event followed until the end of the
 FUW),
 \item the duration of the episode is the interval between the episode start
 and episode end (and may include the gap days at the end, in the latter
 condition described above),
 \item the number of gap days after the end of the episode can be computed
 as all values larger than the permissible gap and 0 otherwise,
 \item if medication change starts new episode, then previous episode ends
 when the last supply is finished (irrespective of the length of gap compared
 to a maximum permissible gap); any days before the date of the new
 medication supply are considered a gap; this maintains consistency with gaps
 between episodes (whether they are constructed based on the maximum
 permissible gap rule or the medication change rule).
}
}
