% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/adherer.R
\name{getEventsToSlidingWindowsMapping}
\alias{getEventsToSlidingWindowsMapping}
\title{getEventsToSlidingWindowsMapping}
\usage{
getEventsToSlidingWindowsMapping(x)
}
\arguments{
\item{x}{is an \code{CMA_sliding_window object}.}
}
\value{
The mapping between events and episodes, if it exists as the
\code{mapping.windows.to.events} component of the \code{CMA_sliding_window object}
object, or \code{NULL} otherwise.
}
\description{
This function returns the event-to-sliding-window mapping, if this information exists.
}
\details{
There are cases where it is interesting to know which events belong to which
sliding windows and which events have been actually used in computing the simple CMA
for each sliding window
This information can be returned by \code{CMA_sliding_window()} if the
parameter \code{return.mapping.events.episodes} is set to \code{TRUE}.
}
